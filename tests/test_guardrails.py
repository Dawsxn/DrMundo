"""Unit tests for the deterministic guardrail + memory logic (no API calls)."""

from agent.format import DISCLAIMER
from agent.memory import SessionMemory
from agent.schemas import Answer, HospitalBreakdown
from guardrails.output_guard import check_output
from guardrails.pii import redact


# --- PII redaction --------------------------------------------------------------------
def test_pii_redacts_email_and_phone():
    text = "reach me at juan@gmail.com or 0917-123-4567"
    clean, found = redact(text)
    assert "EMAIL" in found and "PHONE" in found
    assert "juan@gmail.com" not in clean and "0917" not in clean


def test_pii_preserves_prices_and_rvs_codes():
    # Money amounts and 5-digit RVS codes must NOT be treated as PII.
    clean, found = redact("appendectomy 44950 costs 75,000 to 220,000")
    assert found == []
    assert "44950" in clean and "75,000" in clean


# --- Output grounding guard -----------------------------------------------------------
def _covered_answer(answer_text: str) -> Answer:
    return Answer(
        status="answered", path="covered", query="q", answer_text=answer_text,
        procedure_or_service="APPENDECTOMY;", case_rate=46800.0,
        price_low=75000, price_high=220000, oop_low=28200, oop_high=173200,
        fully_covered=False, as_of="2026",
        hospitals=[HospitalBreakdown(hospital="Chong Hua Hospital", price_low=75000,
                                     price_high=140000, oop_low=28200, oop_high=93200)],
    )


def test_output_guard_keeps_grounded_prose():
    ans = _covered_answer("Case rate ₱46,800; price ₱75,000–₱220,000. " + DISCLAIMER)
    out, report = check_output(ans)
    assert report.grounded is True and report.replaced is False


def test_output_guard_replaces_ungrounded_number():
    # ₱999,999 is not in the grounded set -> prose is thrown away and rebuilt.
    ans = _covered_answer("This actually costs ₱999,999 total.")
    out, report = check_output(ans)
    assert report.grounded is False
    assert 999999 in report.violations
    assert report.replaced is True
    assert "999,999" not in out.answer_text          # ungrounded figure gone
    assert "46,800" in out.answer_text                # grounded figures present


def test_output_guard_appends_disclaimer():
    ans = _covered_answer("Case rate ₱46,800.")
    out, _ = check_output(ans)
    assert DISCLAIMER in out.answer_text


def test_output_guard_adds_not_covered_note_for_outpatient():
    ans = Answer(status="answered", path="outpatient", query="q",
                 answer_text="The price range is ₱7,000–₱16,000.",
                 procedure_or_service="CT Scan (plain)", price_low=7000, price_high=16000,
                 as_of="2026")
    out, _ = check_output(ans)
    assert "not covered by philhealth" in out.answer_text.lower()


# --- Session memory -------------------------------------------------------------------
def test_memory_fifo_eviction():
    mem = SessionMemory(max_turns=4)
    for i in range(6):
        mem.add_user(f"q{i}")
    assert len(mem.history()) == 4
    assert mem.history()[0]["content"] == "q2"   # oldest two evicted
