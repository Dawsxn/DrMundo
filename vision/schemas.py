"""Pydantic schemas for the document-extraction stage (Scope v2).

What a doctor's request slip becomes on the way in: an image -> redaction -> OCR spans
-> LLM normalisation -> `RequestSlip`. Nothing downstream ever sees the image.

Two rules are enforced here rather than left to convention:
  - `RequestSlip.redacted` must be True. An unredacted slip is not constructible, so
    "we forgot to redact" fails at the type boundary instead of at review time.
  - `ExtractedItem` keeps `raw_text` (verbatim, what OCR saw) separate from `normalized`
    (the canonical guess). Collapsing them makes it impossible to tell whether a bad
    answer came from the OCR stage or the matching stage -- and those are owned by
    different people.

This module deliberately imports nothing but pydantic and the stdlib. `pricing/` depends
on it, and `pricing/` must stay free of OCR/vision dependencies.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# What kind of thing the slip is asking for. Drives routing: only `procedure` items can
# ever attract a PhilHealth case rate (see pricing/waterfall.py rule W2).
ItemKind = Literal["procedure", "imaging", "lab", "unknown"]


class ExtractedItem(BaseModel):
    """One line read off a request slip, before any pricing is attempted."""

    raw_text: str = Field(..., description="Verbatim, exactly as OCR read it.")
    normalized: Optional[str] = Field(
        None, description="Canonical name guess; None when the text could not be resolved."
    )
    kind: ItemKind = "unknown"
    ocr_confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: Optional[tuple[int, int, int, int]] = Field(
        None, description="(x0, y0, x1, y1) in the redacted raster, when the model reports one."
    )


class RequestSlip(BaseModel):
    """A single doctor's request, fully extracted and safe to hold in memory."""

    items: list[ExtractedItem] = Field(default_factory=list)
    image_sha256: str = Field(..., description="Hash of the REDACTED raster, not the original.")
    redacted: bool

    @field_validator("redacted")
    @classmethod
    def _must_be_redacted(cls, v: bool) -> bool:
        # Hard failure, not a warning. These are real patient documents; the whole point
        # of the flag is that it cannot be skipped by an agent in a hurry.
        if v is not True:
            raise ValueError(
                "RequestSlip.redacted must be True -- redaction runs before construction "
                "(plan §6 Phase 5, handoff §12)."
            )
        return v
