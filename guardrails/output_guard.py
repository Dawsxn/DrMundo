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
from pricing.schemas import to_display_pesos

# Money-like tokens: optional ₱, digits with optional comma-groups/decimals.
_MONEY_RE = re.compile(r"₱\s?[\d,]+(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{4,}(?:\.\d+)?\b")


@dataclass
class OutputReport:
    grounded: bool = True
    violations: list[float] = field(default_factory=list)
    replaced: bool = False
    notes: list[str] = field(default_factory=list)


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _grounded_values(answer: Answer) -> set[int]:
    vals: set[int] = set()

    for v in (answer.case_rate, answer.price_low, answer.price_high,
              answer.oop_low, answer.oop_high):
        if v is not None:
            vals.add(round(v))
    for h in answer.hospitals or []:
        for v in (h.price_low, h.price_high, h.oop_low, h.oop_high):
            if v is not None:
                vals.add(round(v))

    # Scope v2 `as_of` values are dates like "August 31, 2023", not bare years. The money
    # regex still catches the 2023, so the year has to be grounded or every dated answer
    # trips the guard.
    if answer.as_of:
        s = str(answer.as_of)
        if s.isdigit():
            vals.add(int(s))
        for m in _YEAR_RE.finditer(s):
            vals.add(int(m.group()))

    vals |= _budget_values(answer)
    vals |= _plan_values(answer.hmo)
    return vals


def _plan_values(plan) -> set[int]:
    """Limits read off the patient's own benefits document.

    Grounded wherever the plan is known, including mid-intake when the budget is withheld
    so that no price reaches the screen. Without this the guard treats "your limit is
    P150,000" as an invention and rebuilds the reply into an empty report.
    """
    if plan is None:
        return set()
    vals: set[int] = set()
    amounts = [plan.mbl_annual, plan.remaining_balance, plan.default_procedure_sublimit,
               plan.outpatient_diagnostics_limit, plan.preexisting_cap]
    amounts += list(plan.procedure_sublimits.values())
    for a in amounts:
        if a is not None:
            vals.add(to_display_pesos(a))
    return vals


def _budget_values(answer: Answer) -> set[int]:
    """Every peso inside a multi-item BudgetEstimate.

    Without this the guard sees a report quoting a range PER ITEM, finds none of those
    numbers among the flat scalar fields, declares them all ungrounded, and rebuilds the
    prose -- silently deleting the itemisation and leaving a report that looks fine and
    says almost nothing.

    Rounding goes through to_display_pesos, the SAME function the renderer uses. If these
    two ever round differently, a correct P12,400.50 renders as 12,401 and grounds as
    12,400, and the guard deletes a true figure while the symptom looks like a
    hallucination.
    """
    b = answer.budget
    if b is None:
        return set()

    vals: set[int] = set()

    def add(*amounts):
        for a in amounts:
            if a is not None:
                vals.add(to_display_pesos(a))

    add(b.gross_low, b.gross_high, b.discount_low, b.discount_high,
        b.philhealth_low, b.philhealth_high, b.hmo_low, b.hmo_high,
        b.prepare_low, b.prepare_high)

    for it in b.priced:
        add(it.price_low, it.price_high, it.case_rate)
        if it.as_of:
            for m in _YEAR_RE.finditer(str(it.as_of)):
                vals.add(int(m.group()))
    for s in b.separate_lines:
        add(s.price_low, s.price_high)
    if b.hmo is not None:
        add(b.hmo.mbl_annual, b.hmo.remaining_balance)
        # Limits read off the patient's own benefits document are data, not prose. Telling
        # them "your plan caps this at P35,000" is exactly the sort of figure this guard
        # exists to protect, and leaving it ungrounded made the guard delete a true
        # sentence and replace it with an empty render.
        add(b.hmo.default_procedure_sublimit, b.hmo.outpatient_diagnostics_limit,
            b.hmo.preexisting_cap, *b.hmo.procedure_sublimits.values())

    return vals


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

    # A budget report is MIXED -- outpatient work-up plus possibly one case-rated
    # procedure -- so the note is driven per item rather than by a single path label.
    elif answer.path == "budget_report" and answer.budget is not None:
        uncovered = [p for p in answer.budget.priced if p.case_rate is None]
        low = answer.answer_text.lower()
        if uncovered and "not covered" not in low and "philhealth" not in low:
            n = len(uncovered)
            answer.answer_text += (
                f"\n\nNote: {n} of these item(s) are outpatient services that PhilHealth "
                f"does not cover."
            )
            report.notes.append("Added per-item not-covered note.")

    # Disclaimer is mandatory on every reply that makes a cost claim. A budget_report turn
    # with no budget attached is an intake QUESTION -- it quotes nothing, and repeating the
    # disclaimer under every question turns it into wallpaper people stop reading, which
    # defeats the point of having it on the turn that matters.
    asks_only = answer.path == "budget_report" and answer.budget is None
    if not asks_only and DISCLAIMER not in answer.answer_text:
        answer.answer_text = f"{answer.answer_text.rstrip()}\n\n{DISCLAIMER}"
        report.notes.append("Appended disclaimer.")

    return answer, report
