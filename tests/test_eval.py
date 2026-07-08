"""Unit tests for the Phase 9b eval scoring (pure logic, no network / no API key).

Verifies score_case/case_passed against synthetic Answer-like objects, the aggregation in
summarize(), and that the shipped dataset.json is well formed.
"""

import json
from pathlib import Path
from types import SimpleNamespace

from eval.scoring import case_passed, score_case, summarize

DATASET = Path(__file__).resolve().parent.parent / "eval" / "dataset.json"


def _answer(**kw):
    base = dict(status="answered", path=None, procedure_or_service=None, case_rate=None,
                oop_low=None, oop_high=None, fully_covered=None, answer_text="")
    base.update(kw)
    return SimpleNamespace(**base)


def test_covered_case_all_checks_pass():
    case = {"bucket": "covered", "expect": {
        "category": "cost", "status": "answered", "path": "covered",
        "service_contains": "appendect", "case_rate": 46800, "oop_expected": True}}
    ans = _answer(status="answered", path="covered",
                  procedure_or_service="APPENDECTOMY;", case_rate=46800, oop_low=28200,
                  oop_high=173200)
    checks = score_case(case, ans, category="cost")
    assert checks == {"category": True, "status": True, "path": True, "match": True,
                      "case_rate": True, "oop": True}
    assert case_passed(checks)


def test_wrong_case_rate_and_path_fail():
    case = {"bucket": "covered", "expect": {"path": "covered", "case_rate": 46800}}
    ans = _answer(path="outpatient", case_rate=99999)
    checks = score_case(case, ans, category="cost")
    assert checks == {"path": False, "case_rate": False}
    assert not case_passed(checks)


def test_outpatient_oop_must_be_absent():
    case = {"bucket": "outpatient", "expect": {
        "path": "outpatient", "oop_expected": False, "not_covered_note": True}}
    good = _answer(path="outpatient", oop_low=None, oop_high=None,
                   answer_text="Price range ... not covered by PhilHealth.")
    assert case_passed(score_case(case, good, category="cost"))

    # An outpatient answer that leaked an OOP value must fail the oop check.
    bad = _answer(path="outpatient", oop_low=0, oop_high=100,
                  answer_text="not covered")
    assert score_case(case, bad, category="cost")["oop"] is False


def test_not_covered_note_detection():
    case = {"bucket": "outpatient", "expect": {"not_covered_note": True}}
    assert score_case(case, _answer(answer_text="This is NOT COVERED."), "cost")["not_covered_note"]
    assert score_case(case, _answer(answer_text="mentions philhealth"), "cost")["not_covered_note"]
    assert score_case(case, _answer(answer_text="no note here"), "cost")["not_covered_note"] is False


def test_out_of_scope_path_null_and_category():
    case = {"bucket": "out_of_scope", "expect": {
        "category": "medical_advice", "status": "out_of_scope", "path": None}}
    ans = _answer(status="out_of_scope", path=None)
    checks = score_case(case, ans, category="medical_advice")
    assert case_passed(checks)
    # Wrong category should fail.
    assert not case_passed(score_case(case, ans, category="out_of_scope"))


def test_empty_expect_passes_vacuously():
    assert case_passed(score_case({"bucket": "x", "expect": {}}, _answer(), "cost"))


def test_summarize_aggregates_sub_metrics():
    records = [
        {"bucket": "covered", "checks": {"path": True, "oop": True, "match": True},
         "passed": True, "latency_ms": 100, "total_tokens": 500, "cost_usd": 0.001},
        {"bucket": "outpatient", "checks": {"path": False, "oop": True},
         "passed": False, "latency_ms": 300, "total_tokens": 400, "cost_usd": 0.0008},
        {"bucket": "out_of_scope", "checks": {"status": True},
         "passed": True, "latency_ms": 50, "total_tokens": 20, "cost_usd": 0.00001},
        {"bucket": "ambiguous", "checks": {"status": False},
         "passed": False, "latency_ms": 200, "total_tokens": 300, "cost_usd": 0.0005},
    ]
    s = summarize(records)
    assert s["n"] == 4
    assert s["passed"] == 2
    assert s["pass_rate"] == 0.5
    assert s["routing_accuracy"] == 0.5           # covered+outpatient path: 1 of 2
    assert s["coverage_oop_accuracy"] == 1.0       # both oop checks true
    assert s["refusal_accuracy"] == 1.0
    assert s["clarification_accuracy"] == 0.0
    assert s["total_tokens"] == 1220


def test_dataset_is_well_formed():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) >= 25, "handoff asks for 25-30+ cases"
    buckets = {"covered", "outpatient", "ambiguous", "out_of_scope"}
    ids = set()
    for c in cases:
        assert c["id"] not in ids, f"duplicate id {c['id']}"
        ids.add(c["id"])
        assert c["question"].strip()
        assert c["bucket"] in buckets
        assert isinstance(c.get("expect"), dict) and c["expect"]
    # Every bucket is represented.
    assert buckets <= {c["bucket"] for c in cases}
