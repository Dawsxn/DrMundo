"""Raster redaction. Runs FIRST, before any reader sees an image.

Redaction happens in the PIXELS, not as a PDF annotation or an overlay: annotations can
be peeled off, and a "redacted" PDF that still carries the original text underneath is
worse than no redaction, because it looks safe. Here the pixels are destroyed and the
original is never written anywhere under the repo.

What gets covered on a Philippine request slip: the patient block (name, address, age/sex,
sometimes a PhilHealth number), the physician's licence/PTR/S2 numbers, and any signature.
Test names and section headings must SURVIVE -- they are the entire point of reading the
document.

This module reports what it covered through the same `pii_found` vocabulary as
`guardrails/pii.py`, so a redaction is visible in MLflow next to the text-regex findings.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image, ImageDraw

# Shared vocabulary with guardrails/pii.py::RASTER_PII_LABELS.
PATIENT_BLOCK = "PATIENT_NAME"
PATIENT_ADDRESS = "PATIENT_ADDRESS"
POLICY_NUMBER = "POLICY_NUMBER"
SIGNATURE = "SIGNATURE"

Box = tuple[int, int, int, int]   # (x0, y0, x1, y1) in pixels


@dataclass
class RedactionResult:
    """The redacted image plus an account of what was destroyed."""

    image: Image.Image
    labels: list[str] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)
    sha256: str = ""

    @property
    def redacted(self) -> bool:
        return bool(self.boxes)


def _sha256(img: Image.Image) -> str:
    return hashlib.sha256(img.tobytes()).hexdigest()


def redact_regions(
    image: Image.Image,
    boxes: Sequence[Box],
    labels: Optional[Sequence[str]] = None,
    fill: str = "black",
) -> RedactionResult:
    """Paint solid rectangles over `boxes`. Destructive by design.

    Works on a copy, so the caller's original object is untouched -- but the caller must
    still not persist that original anywhere under the repo.
    """
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    for box in boxes:
        draw.rectangle(box, fill=fill)
    return RedactionResult(
        image=out,
        labels=sorted(set(labels or [])),
        boxes=list(boxes),
        sha256=_sha256(out),
    )


def redact_header_band(
    image: Image.Image,
    top_fraction: float = 0.0,
    height_fraction: float = 0.18,
) -> RedactionResult:
    """Cover a horizontal band, for templates whose patient block sits in a known place.

    A blunt instrument, and deliberately so: on an unknown layout it is better to destroy
    a band that MIGHT hold a name than to leave one that does. The caller picks the band
    per template -- `tpl_04_halfsheet_compact` puts the patient block at the BOTTOM, so
    this is not always the top.
    """
    w, h = image.size
    y0 = int(h * top_fraction)
    y1 = min(h, int(h * (top_fraction + height_fraction)))
    return redact_regions(
        image,
        [(0, y0, w, y1)],
        labels=[PATIENT_BLOCK, PATIENT_ADDRESS],
    )


def load_and_redact(
    path: Path,
    boxes: Optional[Sequence[Box]] = None,
    labels: Optional[Sequence[str]] = None,
    synthetic: bool = False,
) -> RedactionResult:
    """Open an image and redact it in one step.

    `synthetic=True` marks a generated eval image, which has nothing to redact. It returns
    the image unchanged with an empty label list -- NOT a claim that redaction happened.
    Downstream, `RequestSlip.synthetic()` is the matching constructor, so the distinction
    survives into the type system instead of being lost in a boolean.
    """
    img = Image.open(path)
    if synthetic:
        return RedactionResult(image=img.convert("RGB"), labels=[], boxes=[],
                               sha256=_sha256(img.convert("RGB")))
    if not boxes:
        return redact_header_band(img)
    return redact_regions(img, boxes, labels)
