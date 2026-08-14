"""Pydantic schemas for the pricing stage (Scope v2).

`BudgetEstimate` is the single structured object the report renders and the output
guardrail checks every peso against. Everything on a patient's screen must trace to a
field in here.

MONEY REPRESENTATION -- three layers, on purpose:
  db/       int pesos      (existing convention: data/load_db.py::to_int, queries return int)
  pricing/  Decimal        (the senior/PWD multiplier 0.714286 produces fractions; float
                            would make the numbers unauditable, and auditability is the
                            whole point of this project)
  display   int pesos      via `to_display_pesos()` -- ROUND_HALF_UP, used by BOTH the
                            renderer and guardrails/output_guard.py. If those two round
                            differently, the guard flags correct figures as ungrounded and
                            deletes them, and the symptom looks like a hallucination.

Two hard invariants live here rather than in a linter:
  - `BudgetEstimate` triages every extracted item into exactly one bucket (plan §4).
  - `price_basis == "component"` blocks any claim of full coverage (handoff §5.4).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from vision.schemas import ExtractedItem, ProcedureSource

# A PhilHealth case rate is all-in for an episode. When it exceeds MMC's ceiling price,
# MMC cannot be billing the whole episode -- it is a component charge, and reporting
# "fully covered" against it understates a real bill (handoff §5.4).
PriceBasis = Literal["package", "component"]


def to_display_pesos(amount: Decimal) -> int:
    """Round a Decimal peso amount for display. The ONLY rounding in the project.

    Both the report renderer and the grounding guard must call this. Rounding is
    ROUND_HALF_UP (what a person expects), never Python's default banker's rounding.
    """
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class HMOPlan(BaseModel):
    """Assembled CONVERSATIONALLY (plan §2.3) -- never extracted from an image.

    `remaining_balance` is always patient-stated: it appears on no card, certificate or
    benefits letter, because it changes with every claim and lives in the member portal.
    That single fact is why the document-upload design was dropped.
    """

    provider: Optional[str] = None
    plan_name: Optional[str] = None
    mbl_annual: Optional[Decimal] = Field(None, description="Annual maximum benefit limit.")
    remaining_balance: Optional[Decimal] = Field(
        None, description="ALWAYS patient-stated; on no document."
    )
    coverage_pct: float = Field(1.0, ge=0.0, le=1.0)
    room_entitlement: Optional[str] = None
    covers_outpatient_diagnostics: Optional[bool] = None
    accredited_at_mmc: Optional[bool] = None
    mbl_source: Optional[Literal["published_tier", "patient_stated"]] = None
    exclusions: list[str] = Field(default_factory=list)

    @property
    def needs_verification_note(self) -> bool:
        """True when any figure came from the published-tier table rather than the patient.

        Published tiers are individual/family plans; most PH coverage is employer-provided
        and negotiated, so the figure may not be theirs. The answer is labelling, not
        omission (plan §2.3).
        """
        return self.mbl_source == "published_tier"


class SeparateLine(BaseModel):
    """A cost shown to the patient but deliberately NOT summed into the total.

    Professional fees (excluded by scope) and room & board (length of stay is unknowable
    from a slip, so multiplying invents the largest number on the page -- handoff §8).
    """

    label: str
    price_low: Decimal
    price_high: Decimal
    unit: Optional[str] = Field(None, description="e.g. 'per day' for room & board.")
    note: Optional[str] = None


class PricedItem(BaseModel):
    """An extracted item successfully matched to a priced catalogue entry."""

    item: ExtractedItem
    mmc_code: str
    catalog_name: str
    price_low: Decimal
    price_high: Decimal
    price_basis: Optional[PriceBasis] = None
    rvs_code: Optional[str] = None
    case_rate: Optional[Decimal] = None
    match_confidence: float = Field(..., ge=0.0, le=1.0)
    as_of: Optional[str] = None

    @property
    def blocks_full_coverage_claim(self) -> bool:
        """`component` rows must never be reported as fully covered (handoff §5.4)."""
        return self.price_basis == "component"


class BudgetEstimate(BaseModel):
    """The whole answer: what was priced, what wasn't, and what to prepare."""

    priced: list[PricedItem] = Field(default_factory=list)
    unpriced: list[ExtractedItem] = Field(default_factory=list)
    needs_confirmation: list[ExtractedItem] = Field(default_factory=list)
    # Struck-through rows: shown to the patient, never billed. A visible line proves the
    # reader saw the strike-through, and lets a patient catch a mis-read -- if extraction
    # wrongly cancels a real order, they can see it and say so (plan §0.2).
    cancelled: list[ExtractedItem] = Field(default_factory=list)
    extracted_count: int = Field(
        ..., description="len(RequestSlip.items) this estimate was built from."
    )
    # "none_planned" is a real answer, not a missing one. Routine work-up has no operation
    # behind it, and PhilHealth simply does not apply.
    procedure_source: ProcedureSource = "unknown"
    planned_procedure: str | None = None

    # Every leg is a RANGE, not a scalar. A deduction is min(entitlement, what's left to
    # pay), and "what's left" differs between the low and high ends of the price range --
    # e.g. ESWL is P22,700-70,900 against a P35,100 case rate, so PhilHealth pays P22,700
    # at the low end and P35,100 at the high end. Reporting one number there is false
    # precision of exactly the kind this project exists to avoid.
    gross_low: Decimal = Decimal(0)
    gross_high: Decimal = Decimal(0)
    discount_low: Decimal = Decimal(0)
    discount_high: Decimal = Decimal(0)
    philhealth_low: Decimal = Decimal(0)
    philhealth_high: Decimal = Decimal(0)
    hmo_low: Decimal = Decimal(0)
    hmo_high: Decimal = Decimal(0)
    prepare_low: Decimal = Decimal(0)
    prepare_high: Decimal = Decimal(0)

    separate_lines: list[SeparateLine] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    hmo: Optional[HMOPlan] = None
    senior_or_pwd: bool = False

    @model_validator(mode="after")
    def _every_item_lands_somewhere(self) -> "BudgetEstimate":
        # A silently dropped item understates someone's bill and is invisible in the
        # output -- exactly the class of error that survives review (handoff §10.5).
        # Hard failure, never a warning.
        triaged = (len(self.priced) + len(self.unpriced)
                   + len(self.needs_confirmation) + len(self.cancelled))
        if triaged != self.extracted_count:
            raise ValueError(
                f"item accounting broken: {len(self.priced)} priced + {len(self.unpriced)} "
                f"unpriced + {len(self.needs_confirmation)} needs_confirmation + "
                f"{len(self.cancelled)} cancelled = {triaged}, but {self.extracted_count} "
                f"were extracted. Every item must land in exactly one bucket."
            )
        # A range whose low end exceeds its high end is a arithmetic bug, and it would be
        # rendered to a patient as "prepare P90,000 - P40,000" without this.
        if self.prepare_low > self.prepare_high:
            raise ValueError(
                f"inverted range: prepare_low={self.prepare_low} > "
                f"prepare_high={self.prepare_high}"
            )
        return self

    @property
    def has_component_priced_item(self) -> bool:
        """True when any priced item is a partial price -- blocks 'fully covered'."""
        return any(p.blocks_full_coverage_claim for p in self.priced)
