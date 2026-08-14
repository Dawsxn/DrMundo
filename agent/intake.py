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
    """One question to put to the patient, and the slot it fills.

    `options` and `field` describe how to ASK it, so the UI can render real controls
    rather than parse the prose. A patient offered the actual candidate tests answers
    correctly; one asked to describe them in free text often does not.
    """

    kind: str
    text: str
    options: list[str] = None          # buttons or a radio list
    field: str = None                  # "text" | "number" | None
    subject: str = None                # the raw label a disambiguation is about
    progress: tuple = (0, 0)           # (this question, total) for a quiet counter


# Every question the flow can ask, in order. Used for the progress counter.
ALL_KINDS = (Q_DISAMBIGUATE, Q_PROCEDURE, Q_HMO, Q_SENIOR)

# Published Maxicare tiers, offered as choices. "Other" exists because most Philippine
# coverage is employer-negotiated and matches no public tier; we ask for the limit
# instead of pretending one of these fits.
MAXICARE_PLANS = ["Platinum Plus", "Platinum", "Gold", "Silver", "Other / not sure"]


def _pending_disambiguation(memory) -> Optional[str]:
    est = memory.estimate
    if not est or not est.needs_confirmation:
        return None
    for item in est.needs_confirmation:
        if item.raw_text not in memory.resolved_choices:
            return item.raw_text
    return None


def _progress(memory, kind: str) -> tuple:
    """(nth, total) for the counter shown above a question.

    Disambiguation gets its own count, because it repeats once per unclear item: a slip
    with three faint marks asks three times. Folding those into the main sequence made
    the counter sit on "1 of 4" and then jump backwards, which reads as a bug.

    The fixed questions are counted only when they actually apply, since promising four
    and asking three is a small lie and an overstating progress bar is worse than none.
    """
    if kind == Q_DISAMBIGUATE and memory.estimate is not None:
        unclear = [i.raw_text for i in memory.estimate.needs_confirmation]
        done = len([r for r in unclear if r in memory.resolved_choices])
        return (done + 1, len(unclear))

    fixed = [k for k in ALL_KINDS if k != Q_DISAMBIGUATE]
    answered = len([k for k in memory.asked if k in fixed])
    return (answered + 1, max(len(fixed), answered + 1))


def _pending_item(memory):
    raw = _pending_disambiguation(memory)
    if raw is None or memory.estimate is None:
        return None
    return next((i for i in memory.estimate.needs_confirmation if i.raw_text == raw), None)


def next_question(memory) -> Optional[Question]:
    """The next thing worth asking, or None when there is nothing left."""
    if memory.estimate is None:
        return None

    item = _pending_item(memory)
    if item is not None and Q_DISAMBIGUATE not in memory.asked:
        if item.candidates:
            text = f'Your slip says "{item.raw_text}". Which test did your doctor mean?'
            options = item.candidates + ["Leave it out"]
        else:
            # The mark was faint rather than the name unclear, so the real question is
            # whether it is on the slip at all.
            name = item.normalized or item.raw_text
            text = f'The mark next to "{name}" is faint. Did your doctor order it?'
            options = ["Yes, include it", "No, leave it out"]
        return Question(Q_DISAMBIGUATE, text, options=options, subject=item.raw_text,
                        progress=_progress(memory, Q_DISAMBIGUATE))

    if Q_PROCEDURE not in memory.asked and memory.procedure_source == "unknown":
        return Question(
            Q_PROCEDURE,
            "Is this work-up for a planned operation?",
            options=["Just a check-up", "Yes, for an operation"],
            field="text",
            progress=_progress(memory, Q_PROCEDURE),
        )

    if Q_HMO not in memory.asked and memory.hmo is None:
        return Question(
            Q_HMO,
            "Do you have a Maxicare HMO?",
            options=["No HMO"] + MAXICARE_PLANS,
            field="number",
            progress=_progress(memory, Q_HMO),
        )

    if Q_SENIOR not in memory.asked and memory.senior_or_pwd is None:
        return Question(
            Q_SENIOR,
            "Are you a senior citizen or a PWD? That is a 28.6% reduction on hospital "
            "charges.",
            options=["Yes", "No"],
            progress=_progress(memory, Q_SENIOR),
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


def slots_from_choice(kind: str, value, extra=None) -> dict:
    """Turn a widget answer into slots, with no model call.

    A click is unambiguous, so sending it through the extractor would only add latency,
    cost and a chance of misreading it. Typed replies still go through `parse_answer`.
    """
    slots: dict = {}

    if kind == Q_SENIOR:
        slots["senior_or_pwd"] = (value == "Yes")

    elif kind == Q_PROCEDURE:
        if value == "Just a check-up":
            slots["no_procedure_planned"] = True
        elif extra:
            slots["planned_procedure"] = str(extra)
        else:
            slots["no_procedure_planned"] = True

    elif kind == Q_HMO:
        if value == "No HMO":
            slots["has_hmo"] = False
        else:
            slots["hmo_provider"] = "Maxicare"
            if value and value != "Other / not sure":
                slots["hmo_plan"] = value
            if extra:
                slots["hmo_remaining_balance"] = extra

    elif kind == Q_DISAMBIGUATE:
        if value in ("Leave it out", "No, leave it out"):
            slots["drop_item"] = True
        elif value == "Yes, include it":
            slots["keep_item"] = True
        else:
            slots["chosen_test"] = value

    return slots


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

    # A NEGATIVE only counts against the question actually asked. "Walang operasyon" means
    # no operation, but an extractor reading Tagalog "wala" out of context happily returns
    # has_hmo false, which silently skipped the HMO question entirely and cost the patient
    # their coverage. Positive HMO details are still accepted whenever volunteered, since
    # naming a provider and a balance is unambiguous.
    if slots.get("has_hmo") is False and asked_kind == Q_HMO:
        memory.asked.add(Q_HMO)
    elif any(slots.get(k) for k in ("hmo_provider", "hmo_plan", "hmo_remaining_balance")):
        out["hmo"] = resolve_hmo_plan(
            slots.get("hmo_provider"),
            slots.get("hmo_plan"),
            remaining_balance=to_decimal(slots.get("hmo_remaining_balance")),
        )
        memory.asked.add(Q_HMO)

    # Same asymmetry: a "no" is only trusted against the question that was asked, but a
    # volunteered "senior citizen po ako" is unambiguous and taken whenever it appears.
    senior = slots.get("senior_or_pwd")
    if senior is True or (senior is False and asked_kind == Q_SENIOR):
        out["senior_or_pwd"] = bool(senior)
        memory.asked.add(Q_SENIOR)

    pending = _pending_disambiguation(memory)
    if pending and (slots.get("chosen_test") or slots.get("keep_item")
                    or slots.get("drop_item")):
        # Record the decision either way. "Leave it out" is an answer, and without
        # recording it the same item would be asked about on every subsequent turn.
        choice = ("__drop__" if slots.get("drop_item")
                  else str(slots.get("chosen_test") or "__keep__"))
        memory.record_choice(pending, choice)
        memory.asked.discard(Q_DISAMBIGUATE)   # allow the NEXT unclear item to be asked

    return out
