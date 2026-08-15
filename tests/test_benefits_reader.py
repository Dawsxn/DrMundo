"""The benefits reader, tested offline.

No model call: these exercise the parts that turn a model's payload into an HMOPlan, which
is where a misreading becomes a peso figure. The end-to-end accuracy question lives in
eval/benefits_bench.py, which does call the model and scores against the specimens.
"""

from decimal import Decimal

import pytest

from pricing.schemas import HMOPlan
from vision.benefits import _is_catch_all, _to_result, merge_into


def _result(**payload):
    return _to_result(payload, pages=1, mode="text", seconds=0.0)


def test_a_document_that_states_nothing_produces_nulls():
    """The HR one-pager case. An invented ceiling is worse than a missing one, because a
    patient cannot tell the difference once it is a peso figure on a report."""
    plan = _result(plan_name="Silver", mbl=100_000).plan

    assert plan.mbl_annual == Decimal(100_000)
    assert plan.outpatient_diagnostics_limit is None
    assert plan.professional_fees_within_mbl is None
    assert plan.preexisting_cap is None
    assert plan.procedure_sublimits == {}
    assert plan.default_procedure_sublimit is None


def test_sublimits_are_read_into_the_plan():
    plan = _result(mbl=150_000, procedure_sublimits=[
        {"procedure": "Laparoscopic cholecystectomy", "limit": 60000},
        {"procedure": "Magnetic Resonance Imaging (MRI)", "limit": 18000},
    ]).plan

    assert plan.procedure_sublimits["Laparoscopic cholecystectomy"] == Decimal(60_000)
    assert plan.has_schedule


def test_the_catch_all_row_becomes_the_default_not_a_named_cap():
    """"All other non-conventional procedures" is not a procedure. Left in the named map
    it would never match anything and its cap would silently vanish."""
    plan = _result(mbl=150_000, procedure_sublimits=[
        {"procedure": "Laparoscopic cholecystectomy", "limit": 60000},
        {"procedure": "All other non-conventional but medically necessary procedures",
         "limit": 10000},
    ]).plan

    assert plan.default_procedure_sublimit == Decimal(10_000)
    assert len(plan.procedure_sublimits) == 1


@pytest.mark.parametrize("name", [
    "All other non-conventional but medically necessary procedures",
    "all other procedures",
    "Any other medically necessary procedure",
])
def test_catch_all_wording_variants(name):
    assert _is_catch_all(name)


@pytest.mark.parametrize("name", ["Laparoscopic cholecystectomy", "MRI", "Cryosurgery"])
def test_real_procedures_are_not_catch_alls(name):
    assert not _is_catch_all(name)


def test_a_row_without_an_amount_is_dropped_not_zeroed():
    """A sub-limit of zero would mean "your HMO pays nothing for this", which is a very
    different statement from "the reader could not read the figure"."""
    plan = _result(mbl=150_000, procedure_sublimits=[
        {"procedure": "Something", "limit": None},
        {"procedure": "", "limit": 5000},
    ]).plan

    assert plan.procedure_sublimits == {}


def test_full_cover_is_not_recorded_as_a_coinsurance():
    plan = _result(mbl=150_000, coverage_pct=None).plan

    assert plan.coverage_pct == 1.0


def test_a_stated_coinsurance_is_kept():
    plan = _result(mbl=150_000, coverage_pct=0.8).plan

    assert plan.coverage_pct == 0.8


def test_the_source_is_the_document_not_a_published_tier():
    """Once we have read the patient's own booklet, the report must stop telling them
    their figures came from a published tier that may not be theirs."""
    result = _result(plan_name="Gold", mbl=150_000)

    assert result.plan.schedule_source == "uploaded_document"
    assert result.plan.needs_verification_note is False


def test_merge_keeps_the_patients_own_balance():
    """A booklet states the limit at issue and knows nothing about what has been claimed
    since. The portal figure the patient typed is current and must win."""
    existing = HMOPlan(provider="Maxicare", plan_name="Gold",
                       mbl_annual=Decimal(150_000), remaining_balance=Decimal(40_000),
                       preexisting=True)
    fresh = _result(plan_name="Gold", mbl=150_000,
                    procedure_sublimits=[{"procedure": "Lap chole", "limit": 35000}]).plan

    merged = merge_into(fresh, existing)

    assert merged.remaining_balance == Decimal(40_000)
    assert merged.preexisting is True
    assert merged.procedure_sublimits["Lap chole"] == Decimal(35_000)


def test_merge_keeps_a_cap_the_patient_stated_earlier():
    """Answering the sub-limit question is evidence too, and uploading a booklet that does
    not mention that procedure should not throw the answer away."""
    existing = HMOPlan(mbl_annual=Decimal(150_000),
                       procedure_sublimits={"CATARACT EXTRACTION": Decimal(30_000)})
    fresh = _result(mbl=150_000,
                    procedure_sublimits=[{"procedure": "Lap chole", "limit": 35000}]).plan

    merged = merge_into(fresh, existing)

    assert merged.procedure_sublimits["CATARACT EXTRACTION"] == Decimal(30_000)
    assert merged.procedure_sublimits["Lap chole"] == Decimal(35_000)


def test_merge_with_nothing_to_merge_into():
    fresh = _result(mbl=100_000).plan

    assert merge_into(fresh, None) is fresh
