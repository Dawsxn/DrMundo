"""Guardrail tests for the Scope v2 budget-report path (no API).

The pipeline in GUARDRAIL_PIPELINE.md was built for a single-figure answer. A multi-item
report breaks it in ways that are SILENT, which is why these tests exist: the failure mode
is a report that still looks fine and has quietly lost its itemisation.
"""

from decimal import Decimal

from agent.schemas import Answer
from guardrails.input_guard import check_input
from guardrails.output_guard import _grounded_values, check_output
from guardrails.pii import merge_raster_findings, redact
from pricing.schemas import BudgetEstimate, HMOPlan, PricedItem, SeparateLine
from vision.schemas import ExtractedItem


def _priced(name: str, low: str, high: str, case_rate: str | None = None) -> PricedItem:
    return PricedItem(
        item=ExtractedItem(raw_text=name, normalized=name, kind="lab", ocr_confidence=0.9),
        mmc_code="X",
        catalog_name=name,
        price_low=Decimal(low),
        price_high=Decimal(high),
        case_rate=Decimal(case_rate) if case_rate else None,
        match_confidence=0.9,
        as_of="August 31, 2023",
    )


def _budget() -> BudgetEstimate:
    return BudgetEstimate(
        priced=[
            _priced("CBC (COMPLETE BLOOD COUNT)", "630", "1200"),
            _priced("CHEST PA", "1105", "3400"),
        ],
        unpriced=[ExtractedItem(raw_text="FECALYSIS", kind="lab", ocr_confidence=0.9)],
        extracted_count=3,
        gross_low=Decimal("1735"),
        gross_high=Decimal("4600"),
        prepare_low=Decimal("1735"),
        prepare_high=Decimal("4600"),
        separate_lines=[
            SeparateLine(label="Room & board", price_low=Decimal("1810"),
                         price_high=Decimal("37200"), unit="per day")
        ],
    )


def _answer(text: str, budget: BudgetEstimate | None = None) -> Answer:
    return Answer(
        status="answered",
        path="budget_report",
        query="uploaded slip",
        answer_text=text,
        budget=budget if budget is not None else _budget(),
    )


# ------------------------------------------------------------------ nested grounding
def test_per_item_prices_are_grounded():
    # These live nowhere in the flat scalar fields. Before the fix all four read as
    # ungrounded and the guard deleted the itemisation.
    vals = _grounded_values(_answer("x"))
    for expected in (630, 1200, 1105, 3400):
        assert expected in vals


def test_separate_line_and_total_values_are_grounded():
    vals = _grounded_values(_answer("x"))
    assert 1810 in vals and 37200 in vals   # room & board
    assert 1735 in vals and 4600 in vals    # gross / prepare


def test_correct_itemised_report_survives_untouched():
    text = (
        "Prepare ₱1,735 – ₱4,600.\n"
        "CBC ₱630–1,200 · Chest PA ₱1,105–3,400.\n"
        "Room & board is separate: ₱1,810–₱37,200 per day.\n"
        "Not covered by PhilHealth."
    )
    out, report = check_output(_answer(text))
    assert report.grounded is True
    assert report.replaced is False
    # The itemisation is still there -- this is the whole point.
    assert "630" in out.answer_text and "3,400" in out.answer_text


def test_hallucinated_peso_in_an_itemised_report_is_still_caught():
    # The test that matters. It is easy to "fix" grounding by making the guard permissive.
    text = (
        "Prepare ₱1,735 – ₱4,600.\n"
        "CBC ₱630–1,200 · Chest PA ₱1,105–3,400.\n"
        "There is also a ₱99,999 admission deposit."
    )
    out, report = check_output(_answer(text))
    assert report.grounded is False
    assert 99999.0 in report.violations
    assert report.replaced is True
    assert "99,999" not in out.answer_text


def test_rebuild_preserves_every_bucket():
    # When the guard rebuilds, the fallback render must not drop unpriced items --
    # that is how an understated bill becomes invisible.
    out, report = check_output(_answer("Prepare ₱1,735 – ₱4,600 plus ₱88,888 extra."))
    assert report.replaced is True
    assert "FECALYSIS" in out.answer_text
    assert "Not priced" in out.answer_text


def test_as_of_year_does_not_trip_the_guard():
    # "August 31, 2023" is not a bare year, but the money regex still sees 2023.
    text = "Prepare ₱1,735 – ₱4,600. Prices as of August 31, 2023."
    _, report = check_output(_answer(text))
    assert report.grounded is True


def test_hmo_figures_are_grounded():
    b = _budget()
    b.hmo = HMOPlan(mbl_annual=Decimal("100000"), remaining_balance=Decimal("40000"))
    vals = _grounded_values(_answer("x", b))
    assert 100000 in vals and 40000 in vals


# ------------------------------------------------------------------ per-item note
def test_mixed_report_gets_a_per_item_not_covered_note():
    out, report = check_output(_answer("Prepare ₱1,735 – ₱4,600."))
    assert "does not cover" in out.answer_text
    assert "2 of these" in out.answer_text


def test_note_is_not_duplicated_when_already_present():
    text = "Prepare ₱1,735 – ₱4,600. These are not covered by PhilHealth."
    out, _ = check_output(_answer(text))
    assert out.answer_text.lower().count("not covered") == 1


def test_report_with_every_item_case_rated_gets_no_note():
    b = BudgetEstimate(
        priced=[_priced("LAP CHOLE", "150000", "184000", case_rate="60450")],
        extracted_count=1,
        prepare_low=Decimal("89550"),
        prepare_high=Decimal("123550"),
    )
    out, _ = check_output(_answer("Prepare ₱89,550 – ₱123,550.", b))
    assert "does not cover" not in out.answer_text


# ------------------------------------------------------------------ disclaimer still holds
def test_disclaimer_is_still_appended_to_budget_reports():
    out, _ = check_output(_answer("Prepare ₱1,735 – ₱4,600."))
    assert "Estimates only" in out.answer_text


# ------------------------------------------------------------------ raster PII
def test_raster_labels_merge_with_text_findings():
    _, text_found = redact("email me at a@b.com")
    merged = merge_raster_findings(text_found, ["PATIENT_NAME", "POLICY_NUMBER"])
    assert merged == ["EMAIL", "PATIENT_NAME", "POLICY_NUMBER"]


def test_text_regex_cannot_see_raster_pii():
    # A name printed on a slip is invisible to these patterns -- which is exactly why
    # raster redaction is a second, independent mechanism.
    _, found = redact("Juan dela Cruz")
    assert found == []


# ------------------------------------------------------------------ attachment intake
# These exercise the empty-text short-circuit, which returns before the classifier call,
# so they need no network.
def test_bare_slip_upload_is_allowed():
    # An attachment IS the question. Refusing here would block the app's primary flow.
    v = check_input("", has_attachment=True)
    assert v.allowed is True
    assert v.category == "cost"


def test_empty_input_with_no_attachment_is_refused_helpfully():
    v = check_input("", has_attachment=False)
    assert v.allowed is False
    assert "upload a photo" in v.refusal_message


def test_raster_pii_reaches_the_verdict():
    v = check_input("", has_attachment=True, attachment_pii=["PATIENT_NAME"])
    assert v.pii_found == ["PATIENT_NAME"]
