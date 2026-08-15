"""Short-term session memory: text turns, plus the estimate currently under discussion.

Just enough context for follow-ups like "...and at Chong Hua?" or "...how about an MRI
instead?". We store only the user/assistant *text* turns (not the intermediate tool
calls), capped so the buffer stays small.

Scope v2 adds STRUCTURED state. The §14 refine loop asks one question per turn -- "serum
or 24-hour urine?", "do you have an HMO?" -- and each answer re-prices the SAME slip.
Without somewhere to keep the estimate, every answer would need the patient to upload
their request again, which is the fastest way to make them give up.

Nothing is persisted to disk. Health questions, an extracted slip and a stated HMO
balance must not survive the session.
"""

from dataclasses import dataclass, field
from typing import Optional

from pricing.schemas import BudgetEstimate, HMOPlan
from vision.schemas import ProcedureSource, RequestSlip


@dataclass
class SessionMemory:
    max_turns: int = 20  # keep the last N text turns
    turns: list[dict] = field(default_factory=list)

    # ---- the estimate under discussion (Scope v2) -------------------------------------
    slip: Optional[RequestSlip] = None
    estimate: Optional[BudgetEstimate] = None
    hmo: Optional[HMOPlan] = None
    senior_or_pwd: Optional[bool] = None
    procedure_source: ProcedureSource = "unknown"
    planned_procedure: Optional[str] = None
    # Answers that gate whole legs of the waterfall rather than adjusting a figure.
    admitted: Optional[bool] = None            # inpatient vs outpatient
    philhealth_active: Optional[bool] = None   # no contributions, no case rate
    room_type: Optional[str] = None            # which MMC room, if admitted
    length_of_stay: Optional[int] = None       # days, ASKED never assumed
    hmo_covers_outpatient: Optional[bool] = None
    preexisting: Optional[bool] = None
    # Answers to disambiguation questions: raw_text -> the test_code the patient chose.
    resolved_choices: dict = field(default_factory=dict)
    # Which refine questions have been PUT to the patient. A question answered "no" is
    # still answered, so this is what stops the loop asking the same thing twice.
    asked: set = field(default_factory=set)
    # The question the patient is currently answering, so their reply can be
    # interpreted in context ('yes' means different things to different questions).
    last_asked: object = None
    # Which item the pending sub-limit question is about. A cap is only meaningful
    # attached to the procedure it was quoted for, and by the time the answer arrives the
    # question is gone, so the subject has to be held here.
    sublimit_subject: Optional[str] = None

    def remember_question(self, question) -> None:
        """Record what was just asked, and what it was asked about."""
        self.last_asked = question.kind if question else None
        if question is not None and question.subject:
            self.sublimit_subject = question.subject

    def remember_estimate(self, estimate: BudgetEstimate) -> None:
        """Keep the latest estimate, and carry its context forward.

        The context fields are what let the next turn re-price without re-asking. They
        are copied out of the estimate rather than read through it, so a later partial
        update cannot silently revert an answer the patient already gave.
        """
        self.estimate = estimate
        if estimate.hmo is not None:
            self.hmo = estimate.hmo
        if estimate.senior_or_pwd:
            self.senior_or_pwd = True
        if estimate.procedure_source != "unknown":
            self.procedure_source = estimate.procedure_source
            self.planned_procedure = estimate.planned_procedure

    def record_choice(self, raw_text: str, test_code: str) -> None:
        """Remember how the patient disambiguated a label, so we never ask twice."""
        self.resolved_choices[raw_text] = test_code

    def pending_question_count(self) -> int:
        """How many items still need the patient's input on the current estimate."""
        return len(self.estimate.needs_confirmation) if self.estimate else 0

    def has_estimate(self) -> bool:
        return self.estimate is not None

    def clear_estimate(self) -> None:
        """Drop the slip and everything derived from it. WHO THE PATIENT IS survives.

        The split is by what a new piece of paper can actually change. A new slip means a
        new set of tests, a new room, a new operation. It does not mean a new HMO, a new
        age, or newly lapsed PhilHealth contributions.

        Clearing those was a real bug and an infuriating one: a patient who uploaded their
        benefits booklet and then their request slip was asked "do you have a Maxicare
        HMO?" seconds after sending the document that answered it, and the limits they had
        just supplied were thrown away with the question.

        `preexisting` is cleared even though it feels personal, because it is a property of
        the CONDITION rather than the person, and the next slip may be for a different one.
        """
        from agent.intake import Q_HMO, Q_PHILHEALTH, Q_SENIOR

        self.slip = None
        self.estimate = None
        self.procedure_source = "unknown"
        self.planned_procedure = None
        self.admitted = None
        self.room_type = None
        self.length_of_stay = None
        self.hmo_covers_outpatient = None
        self.preexisting = None
        self.resolved_choices.clear()
        # Keep the record of what we have already put to them, or the questions come back
        # even though the answers survived.
        self.asked &= {Q_HMO, Q_PHILHEALTH, Q_SENIOR}
        self.last_asked = None
        self.sublimit_subject = None

    def add(self, role: str, content: str) -> None:
        if not content:
            return
        self.turns.append({"role": role, "content": content})
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]  # FIFO eviction

    def add_user(self, text: str) -> None:
        self.add("user", text)

    def add_assistant(self, text: str) -> None:
        self.add("assistant", text)

    def history(self) -> list[dict]:
        """Prior turns to prepend as LLM context (excludes the current question)."""
        return list(self.turns)

    def clear(self) -> None:
        """A genuinely fresh start: a new person, not a new slip."""
        self.turns.clear()
        self.clear_estimate()
        self.hmo = None
        self.senior_or_pwd = None
        self.philhealth_active = None
        self.asked.clear()
