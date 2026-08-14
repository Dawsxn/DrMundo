"""The conversational refine loop: which question to ask, and what an answer means.

After a slip is priced, the remaining detail lives in the patient's head rather than on
the page. This module decides what to ask next and turns a free-text reply into structured
slots. The order is plan §14's, chosen by what each answer CHANGES rather than by how much
money it moves:

  1. disambiguation   a wrong item invalidates everything downstream of it
  2. planned operation unlocks PhilHealth, the single largest deduction
  3. HMO               unlocks the second largest
  4. senior / PWD      a percentage off what is left

Two rules that keep it from being annoying:

  - Ask each thing ONCE. A question that has been answered, including answered with "no",
    is never asked again. "No operation planned" is a real answer, not a missing one.
  - Never block. The patient can say "just show me the report" at any point and get one,
    because a number that arrived before every question was answered is still true.
"""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from config import CHAT_MODEL, get_openai_client

# Slot names, also used as the "asked" keys in session memory.
Q_DISAMBIGUATE = "disambiguate"
Q_PROCEDURE = "procedure"
Q_HMO = "hmo"
Q_SENIOR = "senior"

_EXTRACT_SYSTEM = """You turn a patient's reply into structured fields for a medical cost \
estimator. Reply with ONLY JSON. Use null for anything the patient did not say. Never guess.

{
  "has_hmo": true|false|null,
  "hmo_provider": string|null,
  "hmo_plan": string|null,
  "hmo_remaining_balance": number|null,
  "senior_or_pwd": true|false|null,
  "planned_procedure": string|null,
  "no_procedure_planned": true|false|null,
  "chosen_test": string|null,
  "wants_report": true|false|null
}

Guidance:
- "wala akong hmo", "none", "no" to an HMO question -> has_hmo false.
- "maxicare gold, mga 40k na lang" -> provider "Maxicare", plan "Gold", balance 40000.
- Amounts may be Taglish shorthand: "40k" is 40000, "1.5k" is 1500, "P40,000" is 40000.
- "wala namang operasyon", "just a check-up", "routine" -> no_procedure_planned true.
- "para sa opera ko sa apdo" -> planned_procedure "gallbladder surgery".
- "senior po ako", "PWD ako" -> senior_or_pwd true. "hindi" to that question -> false.
- "yung dugo" answering which specimen -> chosen_test "blood".
- "ok na", "that's all", "show me the report" -> wants_report true."""


@dataclass
class Question:
    """One question to put to the patient, and the slot it fills."""

    kind: str
    text: str


def _pending_disambiguation(memory) -> Optional[str]:
    est = memory.estimate
    if not est or not est.needs_confirmation:
        return None
    for item in est.needs_confirmation:
        if item.raw_text not in memory.resolved_choices:
            return item.raw_text
    return None


def next_question(memory) -> Optional[Question]:
    """The next thing worth asking, or None when there is nothing left."""
    if memory.estimate is None:
        return None

    raw = _pending_disambiguation(memory)
    if raw is not None and Q_DISAMBIGUATE not in memory.asked:
        return Question(
            Q_DISAMBIGUATE,
            f'Your slip says "{raw}" and I could not pin that down. Which test did your '
            f"doctor mean?",
        )

    if Q_PROCEDURE not in memory.asked and memory.procedure_source == "unknown":
        return Question(
            Q_PROCEDURE,
            "Is this work-up for a planned operation? If it is, tell me which one and I "
            "can add PhilHealth coverage. If it is just a check-up, say so and I will "
            "leave it out.",
        )

    if Q_HMO not in memory.asked and memory.hmo is None:
        return Question(
            Q_HMO,
            "Do you have an HMO? If you do, tell me the provider and plan, and roughly "
            "how much of your benefit is left this year.",
        )

    if Q_SENIOR not in memory.asked and memory.senior_or_pwd is None:
        return Question(
            Q_SENIOR,
            "Last one: are you a senior citizen or a PWD? That is a 28.6% reduction on "
            "hospital charges, so it is worth checking.",
        )

    return None


def parse_answer(text: str, asked_kind: Optional[str] = None) -> dict:
    """Extract slots from a free-text reply.

    Falls back to an empty dict on any failure. A parse error must not lose the patient's
    turn or invent a value; the caller simply asks again.
    """
    if not (text or "").strip():
        return {}
    hint = f"\n\nThe question just asked was about: {asked_kind}." if asked_kind else ""
    try:
        resp = get_openai_client().chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM + hint},
                {"role": "user", "content": text},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        return {k: v for k, v in data.items() if v is not None}
    except Exception:
        return {}


def to_decimal(value) -> Optional[Decimal]:
    """Money from a model or a human: 40000, "40,000", "P40k" all mean the same."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    cleaned = str(value).lower().replace(",", "").replace("₱", "").replace("php", "")
    cleaned = cleaned.strip()
    # "P40,000" is how people actually write pesos when the glyph is awkward to type.
    # Strip a leading p only when a digit follows, so "pwd" is left alone.
    if cleaned[:1] == "p" and cleaned[1:2].isdigit():
        cleaned = cleaned[1:]
    multiplier = Decimal(1)
    if cleaned.endswith("k"):
        cleaned, multiplier = cleaned[:-1], Decimal(1000)
    elif cleaned.endswith("m"):
        cleaned, multiplier = cleaned[:-1], Decimal(1_000_000)
    try:
        return Decimal(cleaned) * multiplier
    except (InvalidOperation, ValueError):
        return None


def apply_answer(memory, slots: dict, asked_kind: Optional[str]) -> dict:
    """Fold extracted slots into session memory. Returns the refine kwargs to re-price with.

    Marking a question as asked is what stops the loop repeating itself, and it happens
    even when the answer was "no", because "no" is an answer.
    """
    from pricing.hmo import resolve_hmo_plan

    out: dict = {}

    if asked_kind:
        memory.asked.add(asked_kind)

    if slots.get("no_procedure_planned"):
        out["procedure_source"] = "none_planned"
        memory.asked.add(Q_PROCEDURE)
    elif slots.get("planned_procedure"):
        out["procedure_source"] = "patient"
        out["planned_procedure"] = slots["planned_procedure"]
        memory.asked.add(Q_PROCEDURE)

    if slots.get("has_hmo") is False:
        # An explicit "no HMO" closes the question without inventing a plan.
        memory.asked.add(Q_HMO)
        memory.hmo = memory.hmo or None
    elif any(slots.get(k) for k in ("hmo_provider", "hmo_plan", "hmo_remaining_balance")):
        out["hmo"] = resolve_hmo_plan(
            slots.get("hmo_provider"),
            slots.get("hmo_plan"),
            remaining_balance=to_decimal(slots.get("hmo_remaining_balance")),
        )
        memory.asked.add(Q_HMO)

    if slots.get("senior_or_pwd") is not None:
        out["senior_or_pwd"] = bool(slots["senior_or_pwd"])
        memory.asked.add(Q_SENIOR)

    if slots.get("chosen_test") and memory.estimate:
        pending = _pending_disambiguation(memory)
        if pending:
            memory.record_choice(pending, str(slots["chosen_test"]))

    return out
