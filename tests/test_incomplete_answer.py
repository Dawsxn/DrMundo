"""An answer that names an operation but not WHICH one must not be treated as "no".

Pressing "Yes, for an operation" with the field left blank used to fall through to the
same branch as "Just a check-up", recording no_procedure_planned. That is the opposite
of what the patient pressed, and it silently removes the PhilHealth case rate, which is
the single largest deduction in the waterfall. The question now repeats and says what
is missing instead.
"""

import pytest

from agent.intake import Q_PROCEDURE, apply_answer, next_question, slots_from_choice
from agent.memory import SessionMemory
from pricing.schemas import BudgetEstimate


@pytest.fixture
def memory() -> SessionMemory:
    mem = SessionMemory()
    mem.estimate = BudgetEstimate(extracted_count=0)
    mem.admitted = False
    mem.asked.add("admitted")
    return mem


def _press(memory, value: str, extra=None) -> dict:
    """Press a button on the procedure question, the way the API does."""
    slots = slots_from_choice(Q_PROCEDURE, value, extra)
    refine = apply_answer(memory, slots, asked_kind=Q_PROCEDURE)
    return {**slots, **refine}


def test_operation_without_a_name_is_not_recorded_as_no_operation(memory):
    result = _press(memory, "Yes, for an operation")

    assert result.get("_incomplete")                       # says what is missing
    assert not result.get("no_procedure_planned")          # the inverted answer
    assert result.get("procedure_source") != "none_planned"
    assert memory.procedure_source == "unknown"


def test_the_question_is_asked_again_rather_than_closed(memory):
    _press(memory, "Yes, for an operation")

    assert Q_PROCEDURE not in memory.asked
    assert next_question(memory).kind == Q_PROCEDURE


def test_naming_the_operation_answers_it(memory):
    result = _press(memory, "Yes, for an operation", extra="gallbladder surgery")

    assert result["procedure_source"] == "patient"
    assert result["planned_procedure"] == "gallbladder surgery"
    assert Q_PROCEDURE in memory.asked
    assert next_question(memory).kind != Q_PROCEDURE


def test_a_check_up_still_closes_the_question(memory):
    result = _press(memory, "Just a check-up")

    assert result["procedure_source"] == "none_planned"
    assert not result.get("_incomplete")
    assert Q_PROCEDURE in memory.asked
