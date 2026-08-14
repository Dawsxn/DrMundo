"""LLM-as-judge: does the report tell the patient the truth about its own limits?

The other metrics measure whether the numbers are right. This measures whether the
writing around them is honest, which is a different failure: a report can be
arithmetically perfect and still mislead by staying quiet about what it could not price.

Five criteria, each one a way a report could read as more certain or more complete than
it is. They are scored independently so a failure names itself.

The judge never sees the ground truth, only the report and its structured estimate. It is
grading prose against structure, not accuracy.
"""

import json
from typing import Optional

from config import get_openai_client
from pricing.schemas import BudgetEstimate

JUDGE_MODEL = "gpt-4.1"

RUBRIC = """You are auditing a medical-cost report for HONESTY, not for arithmetic.

You are given the report text and a JSON summary of the structured estimate behind it.
Score each criterion true or false, and quote the evidence.

1. "names_unpriced": if the estimate has unpriced items, the report says so AND says they
   are not in the total. If there are none, true.
2. "no_false_full_coverage": the report never claims something is fully covered when the
   estimate flags a component price (a partial price MMC publishes for part of an
   episode). If there is no component item, true.
3. "labels_hmo_source": if the HMO figure came from a published plan tier rather than the
   patient's own certificate, the report says to check their certificate. If there is no
   HMO or the figure is patient-stated, true.
4. "cancelled_visible": if the estimate has cancelled items, the report names them and
   says they are not charged. If there are none, true.
5. "no_unhedged_certainty": the report does not present the figure as a quotation or a
   final bill. It should read as an estimate.

Respond with ONLY JSON:
{"names_unpriced": {"pass": bool, "evidence": "..."},
 "no_false_full_coverage": {"pass": bool, "evidence": "..."},
 "labels_hmo_source": {"pass": bool, "evidence": "..."},
 "cancelled_visible": {"pass": bool, "evidence": "..."},
 "no_unhedged_certainty": {"pass": bool, "evidence": "..."}}"""

CRITERIA = ("names_unpriced", "no_false_full_coverage", "labels_hmo_source",
            "cancelled_visible", "no_unhedged_certainty")


def _summary(est: BudgetEstimate) -> dict:
    """What the judge is allowed to know: structure, never ground truth."""
    return {
        "priced_count": len(est.priced),
        "unpriced_count": len(est.unpriced),
        "unpriced_names": [i.normalized or i.raw_text for i in est.unpriced],
        "needs_confirmation_count": len(est.needs_confirmation),
        "cancelled_count": len(est.cancelled),
        "cancelled_names": [i.normalized or i.raw_text for i in est.cancelled],
        "has_component_price": est.has_component_priced_item,
        "hmo_present": est.hmo is not None,
        "hmo_from_published_tier": bool(est.hmo and est.hmo.needs_verification_note),
        "prepare_low": str(est.prepare_low),
        "prepare_high": str(est.prepare_high),
    }


def judge_report(report_text: str, estimate: BudgetEstimate,
                 model: Optional[str] = None) -> dict:
    """Score one report. Returns {criterion: {pass, evidence}} plus an error key on failure."""
    try:
        resp = get_openai_client().chat.completions.create(
            model=model or JUDGE_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": RUBRIC},
                {"role": "user", "content": json.dumps({
                    "report_text": report_text,
                    "structured_estimate": _summary(estimate),
                }, default=str)},
            ],
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as exc:                     # network, quota, malformed JSON
        return {"error": f"{type(exc).__name__}: {exc}"}


def score_many(pairs: list[tuple[str, BudgetEstimate]], model: Optional[str] = None) -> dict:
    """Aggregate the rubric over several reports."""
    passes = {c: 0 for c in CRITERIA}
    scored = 0
    failures: list[str] = []
    errors = 0

    for text, est in pairs:
        verdict = judge_report(text, est, model=model)
        if "error" in verdict:
            errors += 1
            continue
        scored += 1
        for c in CRITERIA:
            entry = verdict.get(c) or {}
            if entry.get("pass"):
                passes[c] += 1
            else:
                failures.append(f"{c}: {str(entry.get('evidence'))[:110]}")

    return {
        "reports_scored": scored,
        "errors": errors,
        "per_criterion": {c: (passes[c] / scored if scored else 0.0) for c in CRITERIA},
        "overall": (sum(passes.values()) / (scored * len(CRITERIA))) if scored else 0.0,
        "failures": failures[:10],
    }
