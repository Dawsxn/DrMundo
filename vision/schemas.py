"""Pydantic schemas for the document-extraction stage (Scope v2).

What a doctor's request slip becomes on the way in: an image -> redaction -> a reader
(vision LLM or local OCR, both benchmarked per plan §0.2) -> `RequestSlip`. Nothing
downstream ever sees the image.

Three rules are enforced here rather than left to convention:
  - `RequestSlip.redacted` must be True. An unredacted slip is not constructible, so
    "we forgot to redact" fails at the type boundary instead of at review time. Synthetic
    eval images use `RequestSlip.synthetic()` rather than asserting a redaction that never
    happened.
  - `ExtractedItem` keeps `raw_text` (verbatim, what the reader saw) separate from
    `normalized` (human-readable name) and `test_code` (the taxonomy code). Collapsing
    them makes it impossible to tell whether a bad answer came from the reading stage or
    the resolving stage, and those are owned by different people.
  - `state` distinguishes an ORDERED test from a CANCELLED one. A struck-through row is a
    test the doctor crossed out; pricing it bills a patient for something they were told
    not to have.

This module deliberately imports nothing but pydantic and the stdlib. `pricing/` depends
on it, and `pricing/` must stay free of vision dependencies.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# What kind of thing the slip is asking for. Drives routing: only `procedure` items can
# ever attract a PhilHealth case rate (see pricing/waterfall.py rule W2). The other three
# behave identically for pricing and are distinguished to match MMC's own categories in
# hospital_prices (Laboratory / Imaging / Diagnostic), so a report can say which it is.
ItemKind = Literal["procedure", "imaging", "lab", "diagnostic", "unknown"]

# Ordered vs crossed out. Defaults to ordered, so an extractor that knows nothing about
# cancellation cannot silently mark real orders as cancelled -- the failure it CAN cause
# (billing a cancelled test) is caught by the eval set's 45 cancelled rows.
ItemState = Literal["ordered", "cancelled"]

# Where the planned procedure came from. "none_planned" is a real answer, not a missing
# one: routine and precautionary work-up has no operation behind it, and an agent that
# cannot represent that will keep asking a patient who is simply getting bloodwork.
ProcedureSource = Literal["slip", "patient", "none_planned", "unknown"]


class ExtractedItem(BaseModel):
    """One line read off a request slip, before any pricing is attempted."""

    raw_text: str = Field(..., description="Verbatim, exactly as the reader saw it.")
    normalized: Optional[str] = Field(
        None, description="Human-readable canonical name; None when unresolved."
    )
    test_code: Optional[str] = Field(
        None, description="Taxonomy code (e.g. CBC, TROPONIN_I). The resolver's output."
    )
    kind: ItemKind = "unknown"
    section: Optional[str] = Field(
        None,
        description=(
            "Section heading the item appeared under. Load-bearing, not decoration: bare "
            "'KUB' appears under both Ultrasound and X-Ray on the same sheet and is only "
            "resolvable from its heading."
        ),
    )
    state: ItemState = "ordered"
    read_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Reader confidence where available. A vision LLM may report none.",
    )
    uncertain: bool = Field(
        False, description="The mark was faint or ambiguous. Independent of read_confidence."
    )
    bbox: Optional[tuple[int, int, int, int]] = Field(
        None, description="(x0, y0, x1, y1) in the redacted raster, when the reader reports one."
    )

    @property
    def is_cancelled(self) -> bool:
        return self.state == "cancelled"


class RequestSlip(BaseModel):
    """A single doctor's request, fully extracted and safe to hold in memory."""

    items: list[ExtractedItem] = Field(default_factory=list)
    image_sha256: str = Field(..., description="Hash of the REDACTED raster, not the original.")
    redacted: bool
    is_laboratory_request: bool = Field(
        True,
        description=(
            "False for documents that are not a request at all. A lab RESULT report is "
            "covered in test names and reference ranges and is still not an order; pricing "
            "it bills a patient for tests they have already had."
        ),
    )
    planned_procedure: Optional[str] = Field(
        None, description="Operation named on the slip itself, when there is one."
    )
    procedure_source: ProcedureSource = "unknown"

    @field_validator("redacted")
    @classmethod
    def _must_be_redacted(cls, v: bool) -> bool:
        # Hard failure, not a warning. These are real patient documents; the whole point
        # of the flag is that it cannot be skipped by an extractor in a hurry.
        if v is not True:
            raise ValueError(
                "RequestSlip.redacted must be True -- redaction runs before construction "
                "(plan §6 Phase 5, handoff §12). For synthetic eval images use "
                "RequestSlip.synthetic()."
            )
        return v

    @classmethod
    def synthetic(cls, **kwargs) -> "RequestSlip":
        """Construct from a synthetic image, which has nothing to redact.

        Kept separate from the normal path on purpose. Passing redacted=True for a
        generated image would assert something that never happened and quietly weaken an
        invariant that exists to protect real patients.
        """
        kwargs.setdefault("image_sha256", "synthetic")
        return cls(redacted=True, **kwargs)

    @property
    def ordered_items(self) -> list[ExtractedItem]:
        """Items the doctor actually wants. Cancelled rows are excluded from pricing."""
        return [i for i in self.items if not i.is_cancelled]

    @property
    def cancelled_items(self) -> list[ExtractedItem]:
        return [i for i in self.items if i.is_cancelled]
