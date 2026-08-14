"""Tests for the 2026-08-15 rulings (plan §0.2): cancelled rows and the procedure tri-state.

Both come from the gold set. 45 rows across 40 forms are struck through, and every form in
the set is a lab request with no operation named, so both paths are exercised by real
eval data rather than hypotheticals.
"""

from decimal import Decimal

import pytest

from agent.format import format_budget_answer
from agent.schemas import Answer
from pricing.schemas import PricedItem
from pricing.waterfall import compute_budget
from report.render import render_html
from vision.schemas import ExtractedItem, RequestSlip


def _item(name: str, *, cancelled: bool = False, kind: str = "lab") -> ExtractedItem:
    return ExtractedItem(
        raw_text=name, normalized=name, kind=kind,
        state="cancelled" if cancelled else "ordered",
        read_confidence=0.9,
    )


def _priced(item: ExtractedItem, low: str = "630", high: str = "1200") -> PricedItem:
    return PricedItem(
        item=item, mmc_code="X", catalog_name=item.normalized or item.raw_text,
        price_low=Decimal(low), price_high=Decimal(high), match_confidence=0.9,
    )


# ------------------------------------------------------------------ cancellation
def test_cancelled_items_are_never_billed():
    est = compute_budget(
        priced=[_priced(_item("CBC"))],
        cancelled=[_item("FBS", cancelled=True)],
    )
    assert est.gross_low == Decimal("630")      # only the CBC
    assert est.prepare_low == Decimal("630")
    assert len(est.cancelled) == 1


def test_a_cancelled_item_reaching_pricing_raises():
    # Billing a test the doctor crossed out is the failure this whole field exists for.
    with pytest.raises(ValueError) as exc:
        compute_budget(priced=[_priced(_item("FBS", cancelled=True))])
    assert "crossed out" in str(exc.value)


def test_cancelled_items_count_toward_the_invariant():
    # Four buckets now. A cancelled row is accounted for, not dropped.
    est = compute_budget(
        priced=[_priced(_item("CBC"))],
        unpriced=[_item("FECALYSIS")],
        needs_confirmation=[_item("CREA")],
        cancelled=[_item("FBS", cancelled=True)],
    )
    assert est.extracted_count == 4


def test_invariant_catches_a_dropped_cancelled_row():
    with pytest.raises(Exception):
        compute_budget(priced=[_priced(_item("CBC"))], extracted_count=2)


def test_cancelled_items_are_visible_on_the_report():
    # Visible, not silent: it proves the reader saw the strike-through, and lets a patient
    # catch a mis-read.
    est = compute_budget(
        priced=[_priced(_item("CBC"))],
        cancelled=[_item("FBS", cancelled=True)],
    )
    html = render_html(est)
    assert "Crossed out by your doctor (1)" in html
    assert "FBS" in html
    assert "not</strong> charged" in html


def test_cancelled_items_appear_in_the_text_fallback_too():
    est = compute_budget(priced=[_priced(_item("CBC"))],
                         cancelled=[_item("FBS", cancelled=True)])
    text = format_budget_answer(Answer(status="answered", path="budget_report",
                                       query="q", answer_text="", budget=est))
    assert "FBS" in text


def test_cancelled_caveat_invites_correction():
    est = compute_budget(cancelled=[_item("FBS", cancelled=True)])
    assert any("looks wrong" in c for c in est.caveats)


def test_slip_helpers_split_ordered_from_cancelled():
    slip = RequestSlip.synthetic(items=[_item("CBC"), _item("FBS", cancelled=True)])
    assert [i.raw_text for i in slip.ordered_items] == ["CBC"]
    assert [i.raw_text for i in slip.cancelled_items] == ["FBS"]


# ------------------------------------------------------------------ procedure tri-state
def test_unknown_procedure_invites_the_question_once():
    est = compute_budget(priced=[_priced(_item("CBC"))], procedure_source="unknown")
    assert any("planned operation" in c for c in est.caveats)


def test_none_planned_closes_the_question():
    # Routine work-up has no operation behind it. A patient getting bloodwork must not be
    # asked twice.
    est = compute_budget(priced=[_priced(_item("CBC"))], procedure_source="none_planned")
    assert not any("tell me which one" in c for c in est.caveats)
    assert any("No operation is planned" in c for c in est.caveats)


def test_procedure_from_slip_is_recorded():
    est = compute_budget(
        priced=[_priced(_item("CBC"))],
        procedure_source="slip",
        planned_procedure="LAPAROSCOPIC CHOLECYSTECTOMY",
    )
    assert est.procedure_source == "slip"
    assert est.planned_procedure == "LAPAROSCOPIC CHOLECYSTECTOMY"
    assert not any("planned operation" in c for c in est.caveats)


def test_procedure_from_patient_is_recorded():
    est = compute_budget(priced=[_priced(_item("CBC"))], procedure_source="patient",
                         planned_procedure="APPENDECTOMY")
    assert est.procedure_source == "patient"
    assert not any("planned operation" in c for c in est.caveats)


def test_slip_can_carry_a_named_procedure():
    # No form in the current dataset does this, but the path exists for the test cases
    # expected later (plan §0.2).
    slip = RequestSlip.synthetic(
        items=[_item("CBC")],
        planned_procedure="CHOLECYSTECTOMY",
        procedure_source="slip",
    )
    assert slip.planned_procedure == "CHOLECYSTECTOMY"


# ------------------------------------------------------------------ dataset contract
def test_synthetic_construction_does_not_assert_a_redaction():
    # Synthetic images have nothing to redact. Passing redacted=True by hand would assert
    # something that never happened and weaken an invariant protecting real patients.
    slip = RequestSlip.synthetic(items=[_item("CBC")])
    assert slip.redacted is True
    assert slip.image_sha256 == "synthetic"


def test_real_slip_still_cannot_skip_redaction():
    with pytest.raises(Exception):
        RequestSlip(items=[], image_sha256="abc", redacted=False)


def test_item_carries_a_test_code_and_section():
    # `normalized` is a name; `test_code` is the taxonomy contract. Bare "KUB" appears
    # under both Ultrasound and X-Ray, so the section heading is load-bearing.
    item = ExtractedItem(raw_text="KUB", normalized="KUB Ultrasound", test_code="US_KUB",
                         kind="imaging", section="ultrasound")
    assert item.test_code == "US_KUB"
    assert item.section == "ultrasound"


def test_read_confidence_is_optional_for_a_vision_model():
    # A vision LLM emits text, not per-span confidence. `uncertain` carries the ground
    # truth's boolean instead.
    item = ExtractedItem(raw_text="FBS", uncertain=True)
    assert item.read_confidence is None
    assert item.uncertain is True


def test_non_request_documents_are_representable():
    # A lab RESULT report is covered in test names and is still not an order.
    slip = RequestSlip.synthetic(items=[], is_laboratory_request=False)
    assert slip.is_laboratory_request is False
