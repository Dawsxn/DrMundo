"""The cost waterfall: priced items -> what the patient should prepare.

PURE PYTHON. No LLM, no I/O, no database. That is the point -- every peso a patient
sees is produced here, so it has to be readable end to end and testable against numbers
someone worked out by hand.

    W0  gross        sum of item ranges, facility/service charges only
    W1  discount     x 0.714286 for senior/PWD  (VAT exemption THEN 20%)
    W2  PhilHealth   case rates, package rows only, procedures only. FACILITY SHARE of
                     each rate (~70%), largest paid in full and the second at half
    W3  HMO          min(remaining balance, MBL, coverage% x what's left)
    W4  prepare      max(0, what's left)

Order matters: W1 runs BEFORE W2 because the two do not commute. Practice is
discount-first -- the discount applies to the hospital's charges and PhilHealth is
deducted from the discounted bill (plan §2.4).

W2 encodes two PhilHealth rules that a naive reading gets wrong in the patient's
disfavour, both of which used to overstate coverage here:
  a case rate splits ~70/30 between hospital and doctor, and our gross is facility only;
  across one admission the largest rate is paid in full and the second at half.

Everything is computed PER ITEM and then summed, because the deductions clamp per item:
a case rate larger than its own procedure's price means that procedure is covered in
full, NOT a credit that subsidises the patient's blood tests.
"""

from decimal import Decimal
from typing import Iterable, Optional

from pricing.textmatch import aligns as _aligns
from pricing.textmatch import norm as _norm
from pricing.schemas import (
    BudgetEstimate,
    HMOPlan,
    PricedItem,
    SeparateLine,
)
from vision.schemas import ExtractedItem, ProcedureSource

# RA 9994: seniors and PWDs get VAT exemption AND 20% off medical services.
#   1 / 1.12 x 0.80 = 0.714285714...  -> a ~28.6% reduction.
# The bug that actually costs money is omitting the VAT exemption and applying only the
# 20%, which is why this is ONE constant and not two multiplications at the call site.
SENIOR_PWD_MULTIPLIER = Decimal("0.714286")

# A PhilHealth case rate is not one pot: it splits into a health-facility fee and a
# professional fee, roughly 70/30. PhilHealth publishes the exact split per code in its
# circular annexes ("Case Rate | Health Facility Fee | Professional Fee"); our dataset
# carries only the total, so the standard ratio stands in for it.
#
# This matters because our gross is FACILITY ONLY -- professional fees are out of scope
# and shown as a separate line. Deducting the whole case rate from a facility-only gross
# credits the patient with the doctor's share as well, and understates what they pay by
# about 30% of the case rate. On a P60,450 cholecystectomy that is P18,135.
PHILHEALTH_FACILITY_SHARE = Decimal("0.70")
PHILHEALTH_PF_SHARE = Decimal("0.30")

# With several case-ratable procedures in one admission, PhilHealth pays the FIRST in
# full and the second at half; later ones draw nothing. Summing them all at 100%, which
# is what this did before, invents coverage that will not arrive.
# Source: PhilHealth All Case Rates policy (PC 0031/0035 s.2013 and successors).
SECOND_CASE_RATE_SHARE = Decimal("0.50")

ZERO = Decimal(0)


def _eligible_for_case_rate(p: PricedItem) -> bool:
    """Can this item attract a PhilHealth case rate?

    Three conditions, all required:
      - it is a PROCEDURE. A case rate is all-in for an admission; applying one to an
        outpatient lab or x-ray double-counts, since the work-up is billed separately.
      - it has a mapped RVS code. 19 real procedures have none, and their coverage is
        UNDETERMINED rather than zero (handoff §5.3).
      - price_basis is 'package'. A 'component' row is a fragment of the episode, so we
        cannot say what PhilHealth pays against it (handoff §5.4).
    """
    return (
        p.item.kind == "procedure"
        and p.rvs_code is not None
        and p.case_rate is not None
        and p.price_basis == "package"
    )


def _case_rate_entitlements(priced: list[PricedItem]) -> dict:
    """How much of each case rate PhilHealth will actually put against the FACILITY bill.

    Two rules compound here, and both cut the figure the naive version produced:

      Only the facility share offsets our gross. The rest of the case rate pays the
      doctor, and professional fees are not in our total, so crediting the whole rate
      would hand the patient the surgeon's subsidy as well.

      Across one admission the largest case rate is paid in full and the second at half.
      Later ones draw nothing. Summing every rate at 100% invents money.

    Returns {id(item): peso amount available against that item's facility charge}.
    """
    eligible = [p for p in priced if _eligible_for_case_rate(p)]
    eligible.sort(key=lambda p: p.case_rate, reverse=True)

    out: dict = {}
    for rank, p in enumerate(eligible):
        if rank == 0:
            portion = Decimal(1)
        elif rank == 1:
            portion = SECOND_CASE_RATE_SHARE
        else:
            portion = ZERO
        out[id(p)] = p.case_rate * PHILHEALTH_FACILITY_SHARE * portion
    return out


def _hmo_cap(hmo: Optional[HMOPlan]) -> Optional[Decimal]:
    """The most this plan could pay, before looking at the bill.

    Remaining balance and annual MBL are both ceilings; the binding one is the smaller.
    Neither present -> no computable cap, so the HMO leg does not fire.

    A pre-existing condition scales the MBL rather than the balance. Group contracts state
    it as a percentage that falls with headcount -- 100% at a hundred members, 10% at
    twenty-six -- so a small employer's plan can pay a tenth of its headline limit.
    """
    if hmo is None:
        return None
    mbl = hmo.mbl_annual
    if mbl is not None and hmo.preexisting and hmo.preexisting_pct_of_mbl is not None:
        mbl = mbl * hmo.preexisting_pct_of_mbl
    caps = [c for c in (hmo.remaining_balance, mbl) if c is not None]
    if hmo.preexisting and hmo.preexisting_cap is not None:
        caps.append(hmo.preexisting_cap)
    return min(caps) if caps else None


def _is_outpatient_kind(p: PricedItem) -> bool:
    """Labs, imaging and diagnostics: what a schedule caps as one outpatient pool."""
    return p.item.kind in ("lab", "imaging", "diagnostic")


def _sublimit_for(p: PricedItem, hmo: Optional[HMOPlan]) -> Optional[Decimal]:
    """This item's own cap under the schedule of benefits, or None if it has none.

    Three ways in, most specific first:

      the RVS code, when the schedule was keyed by code. Unambiguous.
      the procedure NAME, matched at a word boundary. A schedule says "Laparoscopic
        cholecystectomy" where MMC says "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE", so the
        keys never match exactly and raw substring matching is how "Crea" once matched
        "pan-CREA-s" and priced a P740 blood test at P16,800.
      the schedule's catch-all for procedures it did not name.

    An unmatched key is IGNORED, never applied to the nearest-looking row. A cap attached
    to the wrong item removes coverage the patient actually has.
    """
    if hmo is None or not hmo.has_schedule:
        return None

    for key, amount in hmo.procedure_sublimits.items():
        if p.rvs_code and key.strip() == p.rvs_code:
            return amount

    for key, amount in hmo.procedure_sublimits.items():
        norm = _norm(key)
        if len(norm) >= 4 and (_aligns(norm, p.catalog_name)
                               or _aligns(norm, p.item.normalized or p.item.raw_text)):
            return amount

    if _is_outpatient_kind(p):
        return None                    # labs draw on the outpatient pool, not this one
    return hmo.default_procedure_sublimit


def _hmo_payable(
    priced: list[PricedItem],
    hmo: HMOPlan,
    cap: Decimal,
    multiplier: Decimal,
    entitlement: dict,
    end: str,
) -> Decimal:
    """What the HMO pays across the whole bill, at one end of the price range.

    The order the ceilings apply in is the opposite of the intuition, and getting it
    backwards is what overstated coverage tenfold:

      PER ITEM   the procedure's own sub-limit binds first. It is unaffected by what the
                 rest of the bill costs, so it has to be applied before anything is pooled.
      PER POOL   outpatient labs and imaging share one ceiling of their own, separate from
                 the procedures.
      OVERALL    the MBL, or the balance left on it, binds last across everything.

    Run in any other order, a P35,000 cholecystectomy cap on a P150,000 limit yields the
    P150,000. The sub-limit is the number the patient will actually be paid.
    """
    pct = Decimal(str(hmo.coverage_pct))
    total = ZERO
    outpatient_used = ZERO
    outpatient_cap = hmo.outpatient_diagnostics_limit

    for p in priced:
        price = p.price_low if end == "low" else p.price_high
        # What the HMO sees is what PhilHealth left, per item, on the discounted price.
        owed = price * multiplier - min(entitlement.get(id(p), ZERO), price * multiplier)
        payable = owed * pct

        sub = _sublimit_for(p, hmo)
        if sub is not None:
            payable = min(payable, sub)

        if outpatient_cap is not None and _is_outpatient_kind(p):
            payable = min(payable, max(ZERO, outpatient_cap - outpatient_used))
            outpatient_used += payable

        total += payable

    return min(cap, total)


def compute_budget(
    *,
    priced: Iterable[PricedItem] = (),
    unpriced: Iterable[ExtractedItem] = (),
    needs_confirmation: Iterable[ExtractedItem] = (),
    cancelled: Iterable[ExtractedItem] = (),
    extracted_count: Optional[int] = None,
    hmo: Optional[HMOPlan] = None,
    senior_or_pwd: bool = False,
    separate_lines: Iterable[SeparateLine] = (),
    procedure_source: ProcedureSource = "unknown",
    planned_procedure: Optional[str] = None,
    philhealth_active: Optional[bool] = None,
    hmo_covers_outpatient: Optional[bool] = None,
    extra_caveats: Iterable[str] = (),
) -> BudgetEstimate:
    """Run the whole waterfall and return the structured estimate."""
    priced = list(priced)
    unpriced = list(unpriced)
    needs_confirmation = list(needs_confirmation)
    cancelled = list(cancelled)
    separate_lines = list(separate_lines)
    if extracted_count is None:
        extracted_count = (len(priced) + len(unpriced)
                           + len(needs_confirmation) + len(cancelled))

    # Cancelled rows must never have been priced in the first place. If one reached here
    # as a PricedItem the caller has a bug, and the patient would be billed for a test
    # their doctor crossed out -- fail loudly rather than quietly charge them.
    billed_cancelled = [p.catalog_name for p in priced if p.item.is_cancelled]
    if billed_cancelled:
        raise ValueError(
            f"cancelled items reached pricing: {', '.join(billed_cancelled)}. A "
            f"struck-through row is a test the doctor crossed out and must never be billed."
        )

    # -------------------------------------------------------------- W0  gross
    gross_low = sum((p.price_low for p in priced), ZERO)
    gross_high = sum((p.price_high for p in priced), ZERO)

    # -------------------------------------------------------------- W1  senior/PWD
    multiplier = SENIOR_PWD_MULTIPLIER if senior_or_pwd else Decimal(1)
    discount_low = gross_low - (gross_low * multiplier)
    discount_high = gross_high - (gross_high * multiplier)

    # -------------------------------------------------------------- W2  PhilHealth
    # Per item, clamped to that item's own discounted price so an over-generous case rate
    # cannot spill onto other line items.
    philhealth_low = ZERO
    philhealth_high = ZERO
    balance_low = ZERO
    balance_high = ZERO

    # An inactive membership pays nothing. Told "no", we do not deduct a case rate the
    # patient will not receive; told nothing, we behave as before rather than assume.
    philhealth_applies = philhealth_active is not False

    # PhilHealth pays the largest case rate in full and the next at half, so rank them
    # before deducting. Ranking by value is what makes the rule favour the patient
    # correctly: the biggest one is the one paid whole.
    entitlement = _case_rate_entitlements(priced) if philhealth_applies else {}

    for p in priced:
        item_low = p.price_low * multiplier
        item_high = p.price_high * multiplier
        share = entitlement.get(id(p), ZERO)
        if share:
            covered_low = min(share, item_low)
            covered_high = min(share, item_high)
        else:
            covered_low = covered_high = ZERO
        philhealth_low += covered_low
        philhealth_high += covered_high
        balance_low += item_low - covered_low
        balance_high += item_high - covered_high

    # -------------------------------------------------------------- W3  HMO
    # Many plans cover outpatient laboratory work only with a referral or an approval
    # letter. Told "no", the benefit does not apply to a bill that is nothing but labs;
    # crediting it anyway would understate what the patient actually pays.
    outpatient_only = all(_is_outpatient_kind(p) for p in priced)
    hmo_applies = not (hmo_covers_outpatient is False and outpatient_only and priced)

    cap = _hmo_cap(hmo) if hmo_applies else None
    if cap is None:
        hmo_low = hmo_high = ZERO
    else:
        hmo_low = _hmo_payable(priced, hmo, cap, multiplier, entitlement, "low")
        hmo_high = _hmo_payable(priced, hmo, cap, multiplier, entitlement, "high")

    # -------------------------------------------------------------- W4  prepare
    prepare_low = max(ZERO, balance_low - hmo_low)
    prepare_high = max(ZERO, balance_high - hmo_high)

    # Two things make the HMO figure a CEILING rather than an expectation, and either one
    # is enough. Without a schedule of benefits we do not know the per-procedure caps that
    # sit under the MBL, and those are what actually bind. And where the surgeon's fee is
    # drawn from the same limit, part of the pot is already spoken for by a fee we have no
    # data to size. Saying "your HMO will pay X" in either case is a promise we cannot keep.
    # The professional-fee reason only applies where there is a procedure to have fees
    # for. A bill of nothing but blood tests has no surgeon, so raising it there would
    # attach a warning to a figure it cannot affect.
    has_procedure = any(p.item.kind == "procedure" for p in priced)
    hmo_upper_bound = bool(
        (hmo_low or hmo_high)
        and hmo is not None
        and (not hmo.has_schedule
             or (hmo.professional_fees_within_mbl and has_procedure))
    )

    return BudgetEstimate(
        priced=priced,
        unpriced=unpriced,
        needs_confirmation=needs_confirmation,
        cancelled=cancelled,
        extracted_count=extracted_count,
        procedure_source=procedure_source,
        planned_procedure=planned_procedure,
        gross_low=gross_low,
        gross_high=gross_high,
        discount_low=discount_low,
        discount_high=discount_high,
        philhealth_low=philhealth_low,
        philhealth_high=philhealth_high,
        hmo_low=hmo_low,
        hmo_high=hmo_high,
        prepare_low=prepare_low,
        prepare_high=prepare_high,
        separate_lines=separate_lines,
        caveats=_build_caveats(priced, unpriced, needs_confirmation, cancelled,
                               hmo, senior_or_pwd, hmo_low, hmo_high, procedure_source,
                               philhealth_active, hmo_covers_outpatient)
                + list(extra_caveats),
        hmo=hmo,
        senior_or_pwd=senior_or_pwd,
        hmo_upper_bound=hmo_upper_bound,
    )


def _build_caveats(
    priced: list[PricedItem],
    unpriced: list[ExtractedItem],
    needs_confirmation: list[ExtractedItem],
    cancelled: list[ExtractedItem],
    hmo: Optional[HMOPlan],
    senior_or_pwd: bool,
    hmo_low: Decimal = Decimal(0),
    hmo_high: Decimal = Decimal(0),
    procedure_source: ProcedureSource = "unknown",
    philhealth_active: Optional[bool] = None,
    hmo_covers_outpatient: Optional[bool] = None,
) -> list[str]:
    """Everything the patient must be told for the number above to be honest.

    These are not decoration. Each one corresponds to a way the figure could be read as
    more certain, or more complete, than it is.
    """
    out: list[str] = []

    components = [p for p in priced if p.blocks_full_coverage_claim]
    if components:
        names = ", ".join(sorted(p.catalog_name for p in components))
        out.append(
            f"MMC's published figure covers only part of: {names}. The actual bill will be "
            f"higher, and PhilHealth's share of the rest cannot be estimated from it."
        )

    undetermined = [
        p for p in priced
        if p.item.kind == "procedure" and (p.rvs_code is None or p.case_rate is None)
    ]
    if undetermined:
        names = ", ".join(sorted(p.catalog_name for p in undetermined))
        out.append(
            f"No PhilHealth case rate is mapped for: {names}. Coverage is undetermined, "
            f"not zero. Check with PhilHealth."
        )

    if unpriced:
        out.append(
            f"{len(unpriced)} item(s) have no published MMC price and are NOT included in "
            f"the total above."
        )

    if needs_confirmation:
        out.append(
            f"{len(needs_confirmation)} item(s) need confirmation before they can be priced."
        )

    if cancelled:
        names = ", ".join(i.normalized or i.raw_text for i in cancelled)
        subject = "these" if len(cancelled) > 1 else "it"
        out.append(
            f"Your doctor crossed out {names}, so {subject} are not included. If that "
            f"looks wrong, tell me and I will price them."
            if len(cancelled) > 1 else
            f"Your doctor crossed out {names}, so it is not included. If that looks "
            f"wrong, tell me and I will price it."
        )

    # The PhilHealth prompt is stateful on purpose. "unknown" invites the question once;
    # "none_planned" closes it, because routine work-up genuinely has no operation behind
    # it and a patient getting bloodwork should not be asked twice.
    if procedure_source == "unknown":
        out.append(
            "If this work-up is for a planned operation, tell me which one and I can add "
            "PhilHealth coverage to the estimate."
        )
    elif procedure_source == "none_planned":
        out.append(
            "No operation is planned, so PhilHealth case rates do not apply to these "
            "outpatient tests."
        )

    if hmo is None or _hmo_cap(hmo) is None:
        out.append("This figure is before any HMO benefit.")
    elif hmo.needs_verification_note:
        out.append(
            "HMO figures are published amounts for that plan tier, not your actual policy. "
            "Check your own certificate."
        )

    if senior_or_pwd:
        out.append(
            "Includes the senior citizen / PWD reduction of 28.6% (VAT exemption plus 20%), "
            "applied to hospital charges before PhilHealth."
        )

    case_rated = [p for p in priced if _eligible_for_case_rate(p)]
    if case_rated and philhealth_active is not False:
        out.append(
            "PhilHealth's case rate is split between the hospital and the doctor, roughly "
            "70/30. Only the hospital share is deducted above; the rest goes against your "
            "surgeon's and anaesthesiologist's fees, which are billed separately."
        )
    if len(case_rated) > 1:
        out.append(
            f"You have {len(case_rated)} procedures that carry a case rate. PhilHealth "
            f"pays the largest in full and the next at half, so the total credited is less "
            f"than the sum of the individual rates."
        )

    if philhealth_active is False:
        out.append(
            "You said your PhilHealth is not active, so no case rate is deducted. If you "
            "settle your contributions before admission, this could drop considerably."
        )

    # The single most important caveat in this list. A plan's headline limit is not what it
    # pays for any particular operation: real schedules cap the expensive ones well below
    # it. Without the schedule we can only bound the figure from above, and a bound
    # presented as an expectation is how someone arrives at the cashier short.
    if hmo is not None and (hmo_low or hmo_high) and not hmo.has_schedule:
        out.append(
            "This is the MOST your HMO could pay, not what it will. Plans cap individual "
            "procedures well below the overall limit, and yours are unknown. Send me your "
            "benefit booklet or Summary of Benefits and I can use your real limits."
        )

    if (hmo is not None and hmo.professional_fees_within_mbl and (hmo_low or hmo_high)
            and any(p.item.kind == "procedure" for p in priced)):
        out.append(
            "Your plan draws the surgeon's and anaesthesiologist's fees from this same "
            "limit. Those fees are not in the total above and we cannot size them, so less "
            "of your limit will be left for the hospital bill than shown."
        )

    capped = [(p.catalog_name, _sublimit_for(p, hmo)) for p in priced]
    capped = [(n, s) for n, s in capped if s is not None]
    if capped:
        named = "; ".join(f"{n.title()} at ₱{s:,.0f}" for n, s in sorted(capped)[:4])
        out.append(
            f"Your plan caps these individually, and the cap applies before the overall "
            f"limit: {named}. Anything above a cap is yours to settle."
        )

    if hmo is not None and hmo.outpatient_diagnostics_limit is not None and any(
            _is_outpatient_kind(p) for p in priced):
        out.append(
            f"Outpatient laboratory and imaging draw on a separate ceiling of "
            f"₱{hmo.outpatient_diagnostics_limit:,.0f} a year under your plan, not on the "
            f"main limit. This assumes none of it has been used yet."
        )

    if (hmo is not None and hmo.preexisting and hmo.preexisting_pct_of_mbl is not None
            and hmo.preexisting_pct_of_mbl < 1):
        pct = hmo.preexisting_pct_of_mbl * 100
        out.append(
            f"Because this condition predates your plan, only {pct:,.0f}% of your limit is "
            f"available for it. That reduction is already applied above."
        )

    if hmo is not None and hmo.limit_assumed_untouched and (hmo_low or hmo_high):
        out.append(
            f"Your plan's limit is ₱{hmo.mbl_annual:,.0f} per illness per year, and this "
            f"assumes none of it has gone on this particular condition yet. If you have "
            f"already claimed for it this year, you will pay up to ₱{hmo_high:,.0f} more "
            f"than shown."
        )
    # Accreditation could not be verified to the standard the rest of this dataset holds.
    # Maxicare publishes no citable static list -- their directory is a live search tool --
    # and the only lists naming MMC are third-party copies from 2015 and 2018. An HMO pays
    # nothing at a facility it has not accredited, so the honest move is to tell the
    # patient how to check rather than assert a status we cannot source.
    if hmo is not None and hmo.accredited_at_mmc is None and (hmo_low or hmo_high):
        out.append(
            "This assumes Makati Medical Center is accredited under your plan. Your HMO "
            "pays nothing at a facility it has not accredited, so confirm it in the "
            "Maxicare provider directory or with their hotline before you go."
        )

    # Only when we could not put a number on it. Where the schedule gave us the percentage
    # the reduction is already in the arithmetic, and saying it "may be too generous"
    # afterwards would contradict a figure we just computed correctly.
    if hmo is not None and hmo.preexisting and hmo.preexisting_pct_of_mbl is None:
        out.append(
            "You said this condition predates your plan. Pre-existing conditions are "
            "capped at a lower amount during the first year of membership, so the HMO "
            "figure above may be too generous. Your certificate states the actual cap."
        )

    if hmo_covers_outpatient is False:
        out.append(
            "Your plan does not cover outpatient laboratory tests, so the HMO benefit is "
            "not applied here."
        )

    if any(p.item.kind in {"lab", "imaging"} for p in priced):
        out.append(
            "Outpatient laboratory and imaging are not PhilHealth-covered, so no case rate "
            "is deducted for them."
        )

    return out
