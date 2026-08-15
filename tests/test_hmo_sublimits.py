"""Per-procedure sub-limits: the ceiling that binds before the MBL does.

A schedule of benefits caps individual procedures well below the plan's headline limit.
Modelling the MBL as the only ceiling credited a Gold plan with ₱107,685 on a
cholecystectomy that its own schedule caps at ₱35,000, and the patient would have arrived
at the cashier ₱72,685 short.
"""

from decimal import Decimal

import pytest

from pricing.schemas import HMOPlan, PricedItem
from pricing.waterfall import compute_budget
from vision.schemas import ExtractedItem


def _procedure(name: str, low: int, high: int, rvs=None, case_rate=None) -> PricedItem:
    return PricedItem(
        item=ExtractedItem(raw_text=name.lower(), normalized=name, kind="procedure"),
        mmc_code="X", catalog_name=name,
        price_low=Decimal(low), price_high=Decimal(high),
        match_confidence=1.0, rvs_code=rvs,
        case_rate=Decimal(case_rate) if case_rate else None,
        price_basis="package" if rvs else None,
    )


def _lab(name: str, low: int, high: int) -> PricedItem:
    return PricedItem(
        item=ExtractedItem(raw_text=name.lower(), normalized=name, kind="lab"),
        mmc_code="X", catalog_name=name,
        price_low=Decimal(low), price_high=Decimal(high), match_confidence=1.0,
    )


@pytest.fixture
def lapchole() -> PricedItem:
    return _procedure("LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE", 150_000, 208_500)


@pytest.fixture
def gold() -> HMOPlan:
    return HMOPlan(provider="Maxicare", plan_name="Gold", mbl_annual=Decimal(150_000))


def test_the_sublimit_binds_not_the_mbl(lapchole, gold):
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Laparoscopic cholecystectomy": Decimal(35_000)}})

    est = compute_budget(priced=[lapchole], hmo=plan)

    assert est.hmo_low == Decimal(35_000)
    assert est.hmo_high == Decimal(35_000)


def test_without_a_schedule_the_mbl_still_binds(lapchole, gold):
    """The old behaviour has to survive, or every plan we know only by name breaks."""
    est = compute_budget(priced=[lapchole], hmo=gold)

    assert est.hmo_high == Decimal(150_000)


def test_a_figure_without_a_schedule_is_flagged_as_a_ceiling(lapchole, gold):
    est = compute_budget(priced=[lapchole], hmo=gold)

    assert est.hmo_upper_bound is True
    assert any("MOST your HMO could pay" in c for c in est.caveats)


def test_a_schedule_removes_the_ceiling_language(lapchole, gold):
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Laparoscopic cholecystectomy": Decimal(35_000)},
        "schedule_source": "uploaded_document"})

    est = compute_budget(priced=[lapchole], hmo=plan)

    assert not any("MOST your HMO could pay" in c for c in est.caveats)


def test_matching_is_word_boundary_not_substring(gold):
    """The Crea/panCREAs lesson, in the sub-limit matcher this time.

    A cap on "Crea" must not attach itself to a pancreas study. Attaching a cap to the
    wrong item silently removes coverage the patient actually has.
    """
    pancreas = _procedure("PANCREAS STUDY", 16_800, 16_800)
    plan = gold.model_copy(update={"procedure_sublimits": {"Crea": Decimal(700)}})

    est = compute_budget(priced=[pancreas], hmo=plan)

    assert est.hmo_high == Decimal(16_800)          # uncapped, not capped at 700


def test_an_rvs_keyed_sublimit_matches_by_code(gold):
    item = _procedure("SOMETHING MMC CALLS SOMETHING ELSE", 100_000, 100_000, rvs="47562")
    plan = gold.model_copy(update={"procedure_sublimits": {"47562": Decimal(30_000)}})

    est = compute_budget(priced=[item], hmo=plan)

    assert est.hmo_high == Decimal(30_000)


def test_the_catch_all_covers_procedures_the_schedule_did_not_name(gold):
    item = _procedure("SOME UNUSUAL OPERATION", 80_000, 80_000)
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Laparoscopic cholecystectomy": Decimal(35_000)},
        "default_procedure_sublimit": Decimal(5_000)})

    est = compute_budget(priced=[item], hmo=plan)

    assert est.hmo_high == Decimal(5_000)


def test_the_catch_all_does_not_swallow_laboratory_work(gold):
    """Labs draw on the outpatient pool. Applying a procedure catch-all to a CBC would
    cap a ₱630 test at a procedure limit that has nothing to do with it."""
    plan = gold.model_copy(update={"default_procedure_sublimit": Decimal(5_000),
                                   "outpatient_diagnostics_limit": Decimal(20_000)})

    est = compute_budget(priced=[_lab("CBC", 630, 630)], hmo=plan)

    assert est.hmo_high == Decimal(630)


def test_outpatient_items_share_one_pool(gold):
    """Three tests at ₱9,000 each against a ₱20,000 ceiling: ₱20,000, not ₱27,000."""
    labs = [_lab(f"TEST {i}", 9_000, 9_000) for i in range(3)]
    plan = gold.model_copy(update={"outpatient_diagnostics_limit": Decimal(20_000)})

    est = compute_budget(priced=labs, hmo=plan)

    assert est.hmo_high == Decimal(20_000)


def test_sublimits_are_per_item_and_the_mbl_pools_them(gold):
    """Two capped procedures: each capped separately, then the total capped by the MBL."""
    a = _procedure("PROCEDURE ALPHA", 100_000, 100_000)
    b = _procedure("PROCEDURE BETA", 100_000, 100_000)
    plan = gold.model_copy(update={
        "mbl_annual": Decimal(60_000),
        "procedure_sublimits": {"Procedure alpha": Decimal(40_000),
                                "Procedure beta": Decimal(40_000)}})

    est = compute_budget(priced=[a, b], hmo=plan)

    assert est.hmo_high == Decimal(60_000)          # 40k + 40k, pooled down to the MBL


def test_preexisting_scales_the_mbl_when_the_percentage_is_known(lapchole, gold):
    plan = gold.model_copy(update={"preexisting": True,
                                   "preexisting_pct_of_mbl": Decimal("0.10")})

    est = compute_budget(priced=[lapchole], hmo=plan)

    assert est.hmo_high == Decimal(15_000)          # 10% of 150,000
    assert any("only 10% of your limit" in c for c in est.caveats)


def test_preexisting_without_a_percentage_stays_a_caveat(lapchole, gold):
    """We must not invent a reduction. Unknown means warn, not guess."""
    plan = gold.model_copy(update={"preexisting": True})

    est = compute_budget(priced=[lapchole], hmo=plan)

    assert est.hmo_high == Decimal(150_000)
    assert any("capped at a lower amount" in c for c in est.caveats)


def test_professional_fees_inside_the_mbl_make_it_a_ceiling(lapchole, gold):
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Laparoscopic cholecystectomy": Decimal(35_000)},
        "professional_fees_within_mbl": True})

    est = compute_budget(priced=[lapchole], hmo=plan)

    assert est.hmo_upper_bound is True
    assert any("surgeon" in c and "same limit" in c for c in est.caveats)


def test_a_sublimit_never_increases_what_the_hmo_pays(gold):
    """A cap above the bill is not a floor. A ₱50,000 cap on a ₱600 test pays ₱600."""
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Small procedure": Decimal(50_000)}})

    est = compute_budget(priced=[_procedure("SMALL PROCEDURE", 600, 600)], hmo=plan)

    assert est.hmo_high == Decimal(600)


def test_philhealth_is_deducted_before_the_hmo_sublimit_applies(gold):
    """The sub-limit applies to what PhilHealth left, not to the gross.

    Applying it to the gross would credit the HMO for money PhilHealth already paid, and
    the patient's total would come out below what they owe.
    """
    item = _procedure("COVERED OP", 100_000, 100_000, rvs="47562", case_rate=60_450)
    plan = gold.model_copy(update={
        "procedure_sublimits": {"Covered op": Decimal(90_000)}})

    est = compute_budget(priced=[item], hmo=plan, philhealth_active=True)

    # PhilHealth's facility share is 60,450 x 0.70 = 42,315, leaving 57,685.
    assert est.philhealth_high == Decimal("42315.0")
    assert est.hmo_high == Decimal("57685.0")       # not the 90,000 cap, not 100,000
    assert est.prepare_high == Decimal(0)
