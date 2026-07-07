"""Output guardrail: grounding check + safety notes.

Every peso figure in the answer text must tie to a number we actually retrieved. If any
money amount in the prose isn't grounded, we don't trust the prose -- we replace it with a
deterministic rendering built from the structured (grounded) fields. We also guarantee the
disclaimer is present and that outpatient answers state they aren't PhilHealth-covered.
"""

import re
from dataclasses import dataclass, field

from agent.format import DISCLAIMER, format_answer
from agent.schemas import Answer

# Money-like tokens: optional ₱, digits with optional comma-groups/decimals.
_MONEY_RE = re.compile(r"₱\s?[\d,]+(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{4,}(?:\.\d+)?\b")


@dataclass
class OutputReport:
    grounded: bool = True
    violations: list[float] = field(default_factory=list)
    replaced: bool = False
    notes: list[str] = field(default_factory=list)


def _grounded_values(answer: Answer) -> set[int]:
    vals: list[float] = []
    for v in (answer.case_rate, answer.price_low, answer.price_high,
              answer.oop_low, answer.oop_high):
        if v is not None:
            vals.append(v)
    for h in answer.hospitals or []:
        for v in (h.price_low, h.price_high, h.oop_low, h.oop_high):
            if v is not None:
                vals.append(v)
    if answer.as_of and str(answer.as_of).isdigit():
        vals.append(float(answer.as_of))
    return {round(v) for v in vals}


def _money_amounts(text: str) -> set[int]:
    out: set[int] = set()
    for tok in _MONEY_RE.findall(text):
        cleaned = tok.replace("₱", "").replace(",", "").strip()
        try:
            out.add(round(float(cleaned)))
        except ValueError:
            continue
    return out


def check_output(answer: Answer) -> tuple[Answer, OutputReport]:
    report = OutputReport()

    # Only answered cost replies carry numbers worth grounding.
    if answer.status == "answered" and answer.path is not None:
        grounded = _grounded_values(answer)
        mentioned = _money_amounts(answer.answer_text)
        ungrounded = sorted(mentioned - grounded)
        if ungrounded:
            report.grounded = False
            report.violations = [float(u) for u in ungrounded]
            answer.answer_text = format_answer(answer)  # rebuild from grounded fields
            report.replaced = True
            report.notes.append("Ungrounded numbers found; replaced prose with grounded render.")

    # Outpatient answers must state they aren't PhilHealth-covered.
    if answer.path == "outpatient":
        low = answer.answer_text.lower()
        if "not covered" not in low and "philhealth" not in low:
            answer.answer_text += "\n\nNote: this outpatient service is not covered by PhilHealth."
            report.notes.append("Added not-covered note.")

    # Disclaimer is mandatory on every reply.
    if DISCLAIMER not in answer.answer_text:
        answer.answer_text = f"{answer.answer_text.rstrip()}\n\n{DISCLAIMER}"
        report.notes.append("Appended disclaimer.")

    return answer, report
