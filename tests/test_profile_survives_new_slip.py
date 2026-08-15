"""Who the patient is survives a new slip. What the slip says does not.

Uploading a benefits booklet and then a request slip asked "do you have a Maxicare HMO?"
seconds after the document that answered it, and threw away the limits that had just been
read. `clear_estimate` was clearing the person along with the paperwork.
"""

from decimal import Decimal

import pytest

from agent.intake import (
    Q_HMO,
    Q_HMO_OUTPATIENT,
    Q_PREEXISTING,
    Q_SENIOR,
    next_question,
)
from agent.memory import SessionMemory
from pricing.schemas import BudgetEstimate, HMOPlan, PricedItem
from vision.schemas import ExtractedItem


def _plan(**kw) -> HMOPlan:
    base = dict(provider="Maxicare", plan_name="Gold", mbl_annual=Decimal(150_000),
                room_entitlement="Regular Private", schedule_source="uploaded_document")
    return HMOPlan(**{**base, **kw})


@pytest.fixture
def memory() -> SessionMemory:
    """A session in which a benefits document has already been read."""
    mem = SessionMemory()
    mem.hmo = _plan(procedure_sublimits={"Laparoscopic cholecystectomy": Decimal(60_000)})
    mem.senior_or_pwd = False
    mem.philhealth_active = True
    mem.asked |= {Q_HMO, Q_SENIOR, "philhealth"}
    return mem


def test_the_plan_survives_a_new_slip(memory):
    memory.clear_estimate()

    assert memory.hmo is not None
    assert memory.hmo.mbl_annual == Decimal(150_000)
    assert memory.hmo.procedure_sublimits["Laparoscopic cholecystectomy"] == Decimal(60_000)


def test_the_hmo_question_is_not_asked_again(memory):
    memory.clear_estimate()
    memory.estimate = BudgetEstimate(extracted_count=0)

    kinds = []
    for _ in range(8):
        q = next_question(memory)
        if q is None:
            break
        kinds.append(q.kind)
        memory.asked.add(q.kind)

    assert Q_HMO not in kinds
    assert Q_SENIOR not in kinds


def test_slip_specific_answers_are_cleared(memory):
    """A new slip really is a new set of tests, a new room, a new operation."""
    memory.admitted = True
    memory.room_type = "SUITE"
    memory.length_of_stay = 3
    memory.procedure_source = "patient"
    memory.planned_procedure = "gallbladder surgery"

    memory.clear_estimate()

    assert memory.admitted is None
    assert memory.room_type is None
    assert memory.length_of_stay is None
    assert memory.procedure_source == "unknown"
    assert memory.planned_procedure is None


def test_preexisting_is_cleared_because_it_belongs_to_the_condition(memory):
    memory.preexisting = True

    memory.clear_estimate()

    assert memory.preexisting is None


def test_clear_is_a_new_person_not_a_new_slip(memory):
    """`/reset` and New chat must forget the patient entirely."""
    memory.clear()

    assert memory.hmo is None
    assert memory.senior_or_pwd is None
    assert memory.philhealth_active is None
    assert memory.asked == set()


def _lab_estimate() -> BudgetEstimate:
    item = PricedItem(
        item=ExtractedItem(raw_text="cbc", normalized="CBC", kind="lab"),
        mmc_code="X", catalog_name="CBC",
        price_low=Decimal(630), price_high=Decimal(630), match_confidence=1.0,
    )
    return BudgetEstimate(priced=[item], extracted_count=1)


def test_a_stated_outpatient_ceiling_answers_the_outpatient_question():
    """The booklet says "labs up to P20,000 a year". Asking whether labs are covered is
    asking the patient to confirm the document they just sent."""
    mem = SessionMemory()
    mem.estimate = _lab_estimate()
    mem.hmo = _plan(outpatient_diagnostics_limit=Decimal(20_000))
    mem.admitted = False
    mem.asked |= {"admitted", "procedure", Q_HMO, Q_SENIOR, "philhealth"}

    kinds = []
    for _ in range(6):
        q = next_question(mem)
        if q is None:
            break
        kinds.append(q.kind)
        mem.asked.add(q.kind)

    assert Q_HMO_OUTPATIENT not in kinds


def test_without_a_stated_ceiling_the_outpatient_question_still_applies():
    mem = SessionMemory()
    mem.estimate = _lab_estimate()
    mem.hmo = _plan()
    mem.admitted = False
    mem.asked |= {"admitted", "procedure", Q_HMO, Q_SENIOR, "philhealth"}

    assert next_question(mem).kind == Q_HMO_OUTPATIENT


def test_the_preexisting_amount_is_only_asked_when_the_document_lacks_it():
    """Whether the condition is pre-existing is the patient's to answer. The CAP is the
    document's, and asking for it twice is what makes the flow feel like a form."""
    mem = SessionMemory()
    mem.estimate = _lab_estimate()
    mem.admitted = False
    mem.asked |= {"admitted", "procedure", Q_HMO, Q_SENIOR, "philhealth",
                  Q_HMO_OUTPATIENT}

    mem.hmo = _plan(preexisting_cap=Decimal(20_000))
    q = next_question(mem)
    assert q.kind == Q_PREEXISTING and q.field is None

    mem.hmo = _plan()
    q = next_question(mem)
    assert q.kind == Q_PREEXISTING and q.field == "number"


def _room_question(entitlement: str):
    mem = SessionMemory()
    mem.estimate = _lab_estimate()
    mem.hmo = _plan(room_entitlement=entitlement)
    mem.admitted = True
    mem.asked |= {"admitted", "procedure", Q_HMO, Q_SENIOR, "philhealth"}
    q = next_question(mem)
    assert q.kind == "room"
    return q


def test_the_room_question_names_the_plans_entitlement():
    q = _room_question("Semi - Private")

    labelled = [o for o in q.options if "your plan covers this" in o]
    assert len(labelled) == 1
    assert labelled[0].startswith("Semi Private")


def test_an_entitlement_mmc_does_not_publish_is_left_unlabelled():
    """Maxicare's "Regular Private" has no MMC equivalent -- MMC publishes SMALL, LARGE and
    PREMIUM LARGE PRIVATE. Guessing which one they meant would tell a patient their plan
    covers a room it may not, so nothing is marked."""
    q = _room_question("Regular Private")

    assert not any("your plan covers this" in o for o in q.options)
