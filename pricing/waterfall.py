"""The cost waterfall: priced items -> what the patient should prepare.

PURE PYTHON. No LLM, no I/O, no database. That is the point -- every peso a patient
sees is produced here, so it has to be readable end to end and testable against numbers
someone worked out by hand.

    W0  gross        sum of item ranges, facility/service charges only
    W1  discount     x 0.714286 for senior/PWD  (VAT exemption THEN 20%)
    W2  PhilHealth   case rates, package rows only, procedures only
    W3  HMO          min(remaining balance, MBL, coverage% x what's left)
    W4  prepare      max(0, what's left)

Order matters: W1 runs BEFORE W2 because the two do not commute. Discounting first then
deducting the case rate differs from the reverse by about P13,400 on a P46,800 case rate
(plan §2.4). Practice is discount-first -- the discount applies to the hospital's charges
and PhilHealth is deducted from the discounted bill.

Everything is computed PER ITEM and then summed, because the deductions clamp per item:
a case rate larger than its own procedure's price means that procedure is covered in
full, NOT a credit that subsidises the patient's blood tests.
"""

from decimal import Decimal
from typing import Iterable, Optional

from pricing.schemas import (
    BudgetEstimate,
    HMOPlan,
    PricedItem,
    SeparateLine,
)
from vision.schemas import ExtractedItem

# RA 9994: seniors and PWDs get VAT exemption AND 20% off medical services.
#   1 / 1.12 x 0.80 = 0.714285714...  -> a ~28.6% reduction.
# The bug that actually costs money is omitting the VAT exemption and applying only the
# 20%, which is why this is ONE constant and not two multiplications at the call site.
SENIOR_PWD_MULTIPLIER = Decimal("0.714286")

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


def _hmo_cap(hmo: Optional[HMOPlan]) -> Optional[Decimal]:
    """The most this plan could pay, before looking at the bill.

    Remaining balance and annual MBL are both ceilings; the binding one is the smaller.
    Neither present -> no computable cap, so the HMO leg does not fire.
    """
    if hmo is None:
        return None
    caps = [c for c in (hmo.remaining_balance, hmo.mbl_annual) if c is not None]
    return min(caps) if caps else None


def compute_budget(
    *,
    priced: Iterable[PricedItem] = (),
    unpriced: Iterable[ExtractedItem] = (),
    needs_confirmation: Iterable[ExtractedItem] = (),
    extracted_count: Optional[int] = None,
    hmo: Optional[HMOPlan] = None,
    senior_or_pwd: bool = False,
    separate_lines: Iterable[SeparateLine] = (),
) -> BudgetEstimate:
    """Run the whole waterfall and return the structured estimate."""
    priced = list(priced)
    unpriced = list(unpriced)
    needs_confirmation = list(needs_confirmation)
    separate_lines = list(separate_lines)
    if extracted_count is None:
        extracted_count = len(priced) + len(unpriced) + len(needs_confirmation)

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

    for p in priced:
        item_low = p.price_low * multiplier
        item_high = p.price_high * multiplier
        if _eligible_for_case_rate(p):
            covered_low = min(p.case_rate, item_low)
            covered_high = min(p.case_rate, item_high)
        else:
            covered_low = covered_high = ZERO
        philhealth_low += covered_low
        philhealth_high += covered_high
        balance_low += item_low - covered_low
        balance_high += item_high - covered_high

    # -------------------------------------------------------------- W3  HMO
    cap = _hmo_cap(hmo)
    if cap is None:
        hmo_low = hmo_high = ZERO
    else:
        pct = Decimal(str(hmo.coverage_pct))
        hmo_low = min(cap, balance_low * pct)
        hmo_high = min(cap, balance_high * pct)

    # -------------------------------------------------------------- W4  prepare
    prepare_low = max(ZERO, balance_low - hmo_low)
    prepare_high = max(ZERO, balance_high - hmo_high)

    return BudgetEstimate(
        priced=priced,
        unpriced=unpriced,
        needs_confirmation=needs_confirmation,
        extracted_count=extracted_count,
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
        caveats=_build_caveats(priced, unpriced, needs_confirmation, hmo, senior_or_pwd),
        hmo=hmo,
        senior_or_pwd=senior_or_pwd,
    )


def _build_caveats(
    priced: list[PricedItem],
    unpriced: list[ExtractedItem],
    needs_confirmation: list[ExtractedItem],
    hmo: Optional[HMOPlan],
    senior_or_pwd: bool,
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

    if any(p.item.kind in {"lab", "imaging"} for p in priced):
        out.append(
            "Outpatient laboratory and imaging are not PhilHealth-covered, so no case rate "
            "is deducted for them."
        )

    return out
