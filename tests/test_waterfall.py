"""Unit tests for the cost waterfall (pure Python -- no DB, no API).

Every expected figure below was worked out by hand and the arithmetic is shown in the
comment above it. These are the audit trail for every peso the app will ever show a
patient, so a failure here means either the maths changed or the maths broke -- check
which before touching the expectation.
"""

from decimal import Decimal

import pytest

from pricing.schemas import HMOPlan, PricedItem, to_display_pesos
from pricing.waterfall import SENIOR_PWD_MULTIPLIER, compute_budget
from vision.schemas import ExtractedItem


def _item(kind: str = "lab", raw: str = "CBC") -> ExtractedItem:
    return ExtractedItem(raw_text=raw, normalized=raw, kind=kind, ocr_confidence=0.95)


def _priced(
    *,
    low: str,
    high: str,
    kind: str = "lab",
    name: str = "SOMETHING",
    rvs: str | None = None,
    case_rate: str | None = None,
    basis: str | None = None,
) -> PricedItem:
    return PricedItem(
        item=_item(kind, name),
        mmc_code="X",
        catalog_name=name,
        price_low=Decimal(low),
        price_high=Decimal(high),
        rvs_code=rvs,
        case_rate=Decimal(case_rate) if case_rate else None,
        price_basis=basis,
        match_confidence=0.9,
    )


# ------------------------------------------------------------------ the constant
def test_multiplier_includes_the_vat_exemption():
    # 1/1.12 x 0.80 = 0.714285714...  The bug that costs money is shipping 0.80.
    exact = (Decimal(1) / Decimal("1.12")) * Decimal("0.80")
    assert abs(SENIOR_PWD_MULTIPLIER - exact) < Decimal("0.000001")
    assert SENIOR_PWD_MULTIPLIER != Decimal("0.80")


# ------------------------------------------------------------------ W0 / W2 basics
def test_package_procedure_deducts_its_case_rate():
    # Laparoscopic cholecystectomy: P150,000-184,000 against a P60,450 case rate.
    # Only the FACILITY share offsets a facility-only gross: 60,450 x 0.70 = 42,315.
    #   low  150,000 - 42,315 = 107,685
    #   high 184,000 - 42,315 = 141,685
    est = compute_budget(
        priced=[_priced(low="150000", high="184000", kind="procedure",
                        name="LAPAROSCOPIC CHOLECYSTECTOMY", rvs="47562",
                        case_rate="60450", basis="package")]
    )
    assert est.gross_low == Decimal("150000")
    assert est.philhealth_low == Decimal("42315.00")
    assert est.prepare_low == Decimal("107685.00")
    assert est.prepare_high == Decimal("141685.00")


def test_case_rate_straddling_the_range_gives_a_range_of_coverage():
    # ESWL: P22,700-70,900 against a P35,100 case rate. THIS is why every leg is a range.
    # Facility share: 35,100 x 0.70 = 24,570.
    #   low  min(24,570, 22,700) = 22,700  -> 22,700 - 22,700 =      0
    #   high min(24,570, 70,900) = 24,570  -> 70,900 - 24,570 = 46,330
    est = compute_budget(
        priced=[_priced(low="22700", high="70900", kind="procedure", name="ESWL",
                        rvs="50590", case_rate="35100", basis="package")]
    )
    assert est.philhealth_low == Decimal("22700")
    assert est.philhealth_high == Decimal("24570.00")
    assert est.prepare_low == Decimal("0")
    assert est.prepare_high == Decimal("46330.00")


def test_excess_case_rate_does_not_subsidise_other_items():
    # The clamp that matters. A P60,450 case rate against a P40,000 procedure covers
    # P40,000 -- the P20,450 excess is NOT a credit against the patient's blood tests.
    #   procedure 40,000 - 40,000 = 0
    #   lab        1,000 -      0 = 1,000
    est = compute_budget(
        priced=[
            _priced(low="40000", high="40000", kind="procedure", name="PROC",
                    rvs="47562", case_rate="60450", basis="package"),
            _priced(low="1000", high="1000", kind="lab", name="CBC"),
        ]
    )
    assert est.philhealth_low == Decimal("40000")
    assert est.prepare_low == Decimal("1000")
    assert est.prepare_high == Decimal("1000")


# ------------------------------------------------------------------ W2 eligibility
def test_labs_never_attract_a_case_rate_even_if_the_data_has_one():
    # A case rate is all-in for an admission; applying one to an outpatient lab
    # double-counts, since the work-up is billed separately.
    est = compute_budget(
        priced=[_priced(low="1000", high="2000", kind="lab", name="CBC",
                        rvs="99999", case_rate="5000", basis="package")]
    )
    assert est.philhealth_low == Decimal("0")
    assert est.prepare_low == Decimal("1000")


def test_component_rows_get_no_deduction_and_a_caveat():
    # RVS 57452 colposcopy: MMC's P4,100 is a fragment of a P15,639 episode.
    est = compute_budget(
        priced=[_priced(low="4100", high="4100", kind="procedure", name="COLPOSCOPY",
                        rvs="57452", case_rate="15639", basis="component")]
    )
    assert est.philhealth_low == Decimal("0")
    assert est.prepare_low == Decimal("4100")
    assert est.has_component_priced_item is True
    assert any("only part" in c for c in est.caveats)


def test_procedure_without_an_rvs_code_reports_undetermined_not_zero():
    # 19 real procedures have no honest RVS match (handoff §5.3).
    est = compute_budget(
        priced=[_priced(low="50000", high="60000", kind="procedure", name="VATS PACKAGE")]
    )
    assert est.philhealth_low == Decimal("0")
    assert any("undetermined" in c for c in est.caveats)


# ------------------------------------------------------------------ W1 ordering
def test_senior_discount_is_applied_before_philhealth():
    # P100,000 procedure, P46,800 case rate (facility share 32,760), senior.
    #   discount first : 100,000 x 0.714286 = 71,428.60 ; -32,760 = 38,668.60
    #   philhealth first: (100,000-32,760) x 0.714286 = 48,028.60
    # They differ by ~P9,360. Practice is discount-first (plan §2.4).
    est = compute_budget(
        priced=[_priced(low="100000", high="100000", kind="procedure", name="APPY",
                        rvs="44950", case_rate="46800", basis="package")],
        senior_or_pwd=True,
    )
    assert est.prepare_low == Decimal("38668.600000")
    wrong_order = (Decimal("100000") - Decimal("32760")) * SENIOR_PWD_MULTIPLIER
    assert abs(wrong_order - est.prepare_low) > Decimal("9000")


def test_vat_exemption_is_not_silently_dropped():
    # Applying only the 20% would give a P2,000 discount here, not P2,857.14.
    est = compute_budget(
        priced=[_priced(low="10000", high="10000", kind="lab", name="PANEL")],
        senior_or_pwd=True,
    )
    assert to_display_pesos(est.prepare_low) == 7143
    assert est.discount_low > Decimal("2800")


def test_no_discount_when_not_senior_or_pwd():
    est = compute_budget(priced=[_priced(low="10000", high="10000")])
    assert est.discount_low == Decimal("0")
    assert est.prepare_low == Decimal("10000")


# ------------------------------------------------------------------ W3 HMO
def test_hmo_is_capped_by_remaining_balance():
    #   balance 100,000-200,000 ; HMO has P40,000 left -> pays 40,000 at both ends
    est = compute_budget(
        priced=[_priced(low="100000", high="200000", kind="lab", name="PANEL")],
        hmo=HMOPlan(remaining_balance=Decimal("40000")),
    )
    assert est.hmo_low == Decimal("40000")
    assert est.prepare_low == Decimal("60000")
    assert est.prepare_high == Decimal("160000")


def test_hmo_binding_cap_is_the_smaller_of_balance_and_mbl():
    est = compute_budget(
        priced=[_priced(low="500000", high="500000", kind="lab", name="BIG")],
        hmo=HMOPlan(mbl_annual=Decimal("100000"), remaining_balance=Decimal("30000")),
    )
    assert est.hmo_low == Decimal("30000")


def test_hmo_never_pays_more_than_the_bill():
    est = compute_budget(
        priced=[_priced(low="1000", high="1000", kind="lab", name="CBC")],
        hmo=HMOPlan(remaining_balance=Decimal("999999")),
    )
    assert est.hmo_low == Decimal("1000")
    assert est.prepare_low == Decimal("0")


def test_partial_coverage_percentage():
    #   balance 10,000 x 80% = 8,000 covered -> prepare 2,000
    est = compute_budget(
        priced=[_priced(low="10000", high="10000", kind="lab", name="PANEL")],
        hmo=HMOPlan(remaining_balance=Decimal("999999"), coverage_pct=0.8),
    )
    assert est.hmo_low == Decimal("8000.0")
    assert est.prepare_low == Decimal("2000.0")


def test_plan_with_no_figures_does_not_fire_the_hmo_leg():
    # A named plan we could not resolve must not silently imply zero coverage.
    est = compute_budget(
        priced=[_priced(low="5000", high="5000", kind="lab", name="CBC")],
        hmo=HMOPlan(provider="Maxicare", plan_name="Gold"),
    )
    assert est.hmo_low == Decimal("0")
    assert any("before any HMO" in c for c in est.caveats)


def test_published_tier_figures_are_labelled_for_verification():
    est = compute_budget(
        priced=[_priced(low="50000", high="50000", kind="lab", name="PANEL")],
        hmo=HMOPlan(mbl_annual=Decimal("100000"), mbl_source="published_tier"),
    )
    assert any("your own certificate" in c for c in est.caveats)


# ------------------------------------------------------------------ W4 / whole thing
def test_all_four_legs_together():
    #   gross      100,000
    #   senior     100,000 x 0.714286        = 71,428.60
    #   philhealth 46,800 x 0.70 = 32,760    -> 38,668.60
    #   hmo        min(20,000, 38,668.60)    = 20,000  -> 18,668.60
    est = compute_budget(
        priced=[_priced(low="100000", high="100000", kind="procedure", name="APPY",
                        rvs="44950", case_rate="46800", basis="package")],
        senior_or_pwd=True,
        hmo=HMOPlan(remaining_balance=Decimal("20000")),
    )
    assert est.philhealth_low == Decimal("32760.00")
    assert est.hmo_low == Decimal("20000")
    assert to_display_pesos(est.prepare_low) == 18669


def test_prepare_never_goes_negative():
    est = compute_budget(
        priced=[_priced(low="1000", high="1000", kind="procedure", name="CHEAP",
                        rvs="1", case_rate="99999", basis="package")],
        hmo=HMOPlan(remaining_balance=Decimal("99999")),
    )
    assert est.prepare_low == Decimal("0")
    assert est.prepare_high == Decimal("0")


def test_all_unpriced_slip_is_a_real_outcome():
    # P0 KNOWN, not P0 owed -- and the caveat must say so.
    est = compute_budget(
        unpriced=[_item("lab", "FECALYSIS"), _item("lab", "SODIUM")],
    )
    assert est.prepare_low == Decimal("0")
    assert est.extracted_count == 2
    assert any("no published MMC price" in c for c in est.caveats)


def test_needs_confirmation_is_reported():
    est = compute_budget(needs_confirmation=[_item("lab", "CREA")])
    assert any("need confirmation" in c for c in est.caveats)


def test_outpatient_items_get_the_not_covered_caveat():
    est = compute_budget(priced=[_priced(low="630", high="1200", kind="lab", name="CBC")])
    assert any("not PhilHealth-covered" in c for c in est.caveats)


def test_item_accounting_invariant_still_holds_through_the_waterfall():
    est = compute_budget(
        priced=[_priced(low="1", high="1")],
        unpriced=[_item()],
        needs_confirmation=[_item()],
    )
    assert est.extracted_count == 3


def test_explicit_extracted_count_mismatch_raises():
    # The waterfall must not paper over a dropped item.
    with pytest.raises(Exception):
        compute_budget(priced=[_priced(low="1", high="1")], extracted_count=5)


# ------------------------------------------------------------------ PhilHealth realism
def test_only_the_facility_share_offsets_a_facility_only_gross():
    """A case rate splits ~70/30 between the hospital and the doctor.

    Professional fees are out of scope and shown as a separate line, so the gross here is
    facility only. Deducting the WHOLE case rate from it hands the patient the surgeon's
    subsidy too, and understates what they owe by 30% of the rate. On a P60,450
    cholecystectomy that is P18,135.
    """
    est = compute_budget(
        priced=[_priced(low="150000", high="184000", kind="procedure", name="CHOLE",
                        rvs="47562", case_rate="60450", basis="package")]
    )
    assert est.philhealth_low == Decimal("60450") * Decimal("0.70")


def test_second_procedure_is_paid_at_half():
    """PhilHealth pays the largest case rate in full and the next at 50%.

    Summing both at 100% invents coverage that will not arrive.
      first  60,450 x 0.70          = 42,315
      second 46,800 x 0.70 x 0.50   = 16,380
    """
    est = compute_budget(priced=[
        _priced(low="200000", high="200000", kind="procedure", name="BIG",
                rvs="47562", case_rate="60450", basis="package"),
        _priced(low="200000", high="200000", kind="procedure", name="SMALLER",
                rvs="44950", case_rate="46800", basis="package"),
    ])
    assert est.philhealth_low == Decimal("42315.00") + Decimal("16380.00")


def test_third_procedure_draws_nothing():
    est = compute_budget(priced=[
        _priced(low="200000", high="200000", kind="procedure", name="A",
                rvs="1", case_rate="60000", basis="package"),
        _priced(low="200000", high="200000", kind="procedure", name="B",
                rvs="2", case_rate="50000", basis="package"),
        _priced(low="200000", high="200000", kind="procedure", name="C",
                rvs="3", case_rate="40000", basis="package"),
    ])
    expected = Decimal("60000") * Decimal("0.70") + Decimal("50000") * Decimal("0.70") * Decimal("0.5")
    assert est.philhealth_low == expected


def test_the_largest_case_rate_is_the_one_paid_in_full():
    # Order of the items must not decide who gets the full rate; value does, because
    # ranking the other way would quietly cost the patient money.
    a = compute_budget(priced=[
        _priced(low="200000", high="200000", kind="procedure", name="SMALL",
                rvs="1", case_rate="20000", basis="package"),
        _priced(low="200000", high="200000", kind="procedure", name="BIG",
                rvs="2", case_rate="60000", basis="package"),
    ])
    expected = Decimal("60000") * Decimal("0.70") + Decimal("20000") * Decimal("0.70") * Decimal("0.5")
    assert a.philhealth_low == expected


def test_inactive_philhealth_deducts_nothing():
    est = compute_budget(
        priced=[_priced(low="150000", high="184000", kind="procedure", name="CHOLE",
                        rvs="47562", case_rate="60450", basis="package")],
        philhealth_active=False,
    )
    assert est.philhealth_low == Decimal("0")
    assert any("not active" in c for c in est.caveats)


def test_hmo_not_applied_when_the_plan_excludes_outpatient_labs():
    est = compute_budget(
        priced=[_priced(low="5000", high="5000", kind="lab", name="PANEL")],
        hmo=HMOPlan(remaining_balance=Decimal("40000")),
        hmo_covers_outpatient=False,
    )
    assert est.hmo_low == Decimal("0")
    assert est.prepare_low == Decimal("5000")
    assert any("does not cover outpatient" in c for c in est.caveats)


# ------------------------------------------------------------------ HMO realism
def test_unknown_balance_says_it_is_assuming_the_full_limit():
    """The limit is PER ILLNESS per year, not one annual pot.

    So a new condition genuinely gets the whole limit even if the member claimed for
    something unrelated last month, which makes this a milder assumption than an annual
    aggregate would be. It is still an assumption when they have already claimed for THIS
    condition, so it is stated with the amount at stake.
    """
    plan = HMOPlan(plan_name="Gold", mbl_annual=Decimal("150000"))
    assert plan.limit_assumed_untouched is True
    est = compute_budget(priced=[_priced(low="80000", high="80000", name="PANEL")],
                         hmo=plan)
    assert any("per illness per year" in c for c in est.caveats)
    assert any("this particular condition" in c for c in est.caveats)


def test_a_preexisting_condition_is_flagged_as_capped_lower():
    # Maxicare covers pre-existing conditions in year one, but at a reduced cap. We
    # cannot know the figure, so we flag rather than invent one.
    plan = HMOPlan(plan_name="Gold", mbl_annual=Decimal("150000"),
                   remaining_balance=Decimal("50000"), preexisting=True)
    est = compute_budget(priced=[_priced(low="80000", high="80000", name="PANEL")],
                         hmo=plan)
    assert any("predates your plan" in c for c in est.caveats)
    assert any("first year" in c for c in est.caveats)


def test_a_stated_balance_is_not_flagged_as_an_assumption():
    plan = HMOPlan(plan_name="Gold", mbl_annual=Decimal("150000"),
                   remaining_balance=Decimal("20000"))
    assert plan.limit_assumed_untouched is False
    est = compute_budget(priced=[_priced(low="80000", high="80000", name="PANEL")],
                         hmo=plan)
    assert est.hmo_low == Decimal("20000")
    assert not any("annual HMO limit is still available" in c for c in est.caveats)
