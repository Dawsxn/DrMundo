"""Pure scoring logic for the eval harness (no network, no imports from the agent).

Kept separate from `run_eval.py` so it can be unit-tested against synthetic answers. A
case's `expect` block lists only the assertions that apply to it; `score_case` checks just
those keys and returns a per-check {name: bool} dict. `case_passed` is the AND of them.
"""

from __future__ import annotations

from typing import Any

# The check keys, in a stable display order.
CHECK_ORDER = ["category", "status", "path", "match", "case_rate", "oop", "not_covered_note"]


def score_case(case: dict, answer: Any, category: str) -> dict[str, bool]:
    """Compare one case's expectations against an Answer-like object + input category.

    `answer` needs the attributes of `agent.schemas.Answer` (status, path,
    procedure_or_service, case_rate, oop_low, oop_high, fully_covered, answer_text)."""
    expect = case.get("expect", {})
    checks: dict[str, bool] = {}

    if "category" in expect:
        checks["category"] = category == expect["category"]

    if "status" in expect:
        checks["status"] = answer.status == expect["status"]

    if "path" in expect:  # null in JSON -> None
        checks["path"] = answer.path == expect["path"]

    if "service_contains" in expect:
        name = (answer.procedure_or_service or "").lower()
        checks["match"] = expect["service_contains"].lower() in name

    if "case_rate" in expect:
        checks["case_rate"] = answer.case_rate == expect["case_rate"]

    if "oop_expected" in expect:
        if expect["oop_expected"]:
            # Covered + priced: an OOP figure OR an explicit fully-covered verdict.
            checks["oop"] = answer.oop_low is not None or bool(answer.fully_covered)
        else:
            # Outpatient: never an out-of-pocket.
            checks["oop"] = answer.oop_low is None and answer.oop_high is None

    if expect.get("not_covered_note"):
        low = (answer.answer_text or "").lower()
        checks["not_covered_note"] = "not covered" in low or "philhealth" in low

    return checks


def case_passed(checks: dict[str, bool]) -> bool:
    """A case passes if every applicable check passed (vacuously true if no checks)."""
    return all(checks.values())


def summarize(records: list[dict]) -> dict:
    """Aggregate per-case records (each: bucket, checks, passed, latency_ms, tokens, cost).

    Returns overall pass rate, per-bucket pass rate, the targeted sub-metrics the handoff
    asks for (routing / refusal / clarification / coverage-OOP), and latency/cost totals."""
    n = len(records)
    passed = sum(r["passed"] for r in records)

    by_bucket: dict[str, list[dict]] = {}
    for r in records:
        by_bucket.setdefault(r["bucket"], []).append(r)

    def rate(rows: list[dict], key: str) -> float | None:
        vals = [rows_r["checks"][key] for rows_r in rows if key in rows_r["checks"]]
        return (sum(vals) / len(vals)) if vals else None

    cost_rows = by_bucket.get("covered", []) + by_bucket.get("outpatient", [])
    latencies = sorted(r["latency_ms"] for r in records)

    return {
        "n": n,
        "passed": passed,
        "pass_rate": passed / n if n else 0.0,
        "bucket_pass_rate": {
            b: sum(r["passed"] for r in rows) / len(rows) for b, rows in by_bucket.items()
        },
        # Targeted sub-metrics (fraction of applicable cases that got it right).
        "routing_accuracy": rate(cost_rows, "path"),
        "refusal_accuracy": rate(by_bucket.get("out_of_scope", []), "status"),
        "clarification_accuracy": rate(by_bucket.get("ambiguous", []), "status"),
        "coverage_oop_accuracy": rate(cost_rows, "oop"),
        "match_accuracy": rate(cost_rows, "match"),
        "avg_latency_ms": sum(latencies) / n if n else 0.0,
        "p95_latency_ms": latencies[int(0.95 * (n - 1))] if n else 0.0,
        "total_tokens": sum(r["total_tokens"] for r in records),
        "total_cost_usd": round(sum(r["cost_usd"] for r in records), 6),
    }
