"""The extraction stage: image -> RequestSlip.

    redact  ->  read  ->  resolve  ->  triage

Each step is someone else's module; this is the wiring and the triage policy. The policy
is the part worth arguing about, so it is spelled out rather than buried:

  - An ambiguous label goes to `needs_confirmation`, never to a price. "PT" without a
    section could be prothrombin time or a pregnancy test, and guessing wrong prices a
    test the patient is not having.
  - An unresolved label ALSO goes to `needs_confirmation`, not to the bin. We read
    something; we owe the patient a question about it rather than a silent omission.
  - A cancelled mark goes to `cancelled` and is never priced, whatever it resolved to.
  - A low-confidence read is flagged `uncertain` and routed to confirmation even when it
    resolved cleanly. Confidence is about whether the mark is THERE, not what it means.
"""

from pathlib import Path
from typing import Optional

from vision.reader import ReadResult
from vision.resolve import resolve
from vision.schemas import ExtractedItem, RequestSlip

# Below this, we do not trust that the mark exists at all. Readers that report no
# confidence (a vision LLM) are unaffected -- `uncertain` carries that signal instead.
CONFIDENCE_FLOOR = 0.55


def _to_item(mark, res) -> ExtractedItem:
    return ExtractedItem(
        raw_text=mark.label,
        normalized=res.canonical_name,
        test_code=res.test_code,
        kind=res.kind,
        section=mark.section,
        state="cancelled" if mark.cancelled else "ordered",
        read_confidence=mark.confidence,
        uncertain=mark.uncertain,
    )


def _low_confidence(mark) -> bool:
    return mark.confidence is not None and mark.confidence < CONFIDENCE_FLOOR


def extract_request(
    read: ReadResult,
    image_sha256: str,
    *,
    synthetic: bool = False,
    planned_procedure: Optional[str] = None,
) -> RequestSlip:
    """Turn a reader's output into a validated RequestSlip.

    `synthetic=True` routes construction through RequestSlip.synthetic(), which is honest
    about the fact that a generated image had nothing to redact.
    """
    items: list[ExtractedItem] = []
    for mark in read.marks:
        res = resolve(mark.label, mark.section)
        item = _to_item(mark, res)
        # Uncertainty from either source survives into the item, so triage can see it.
        if _low_confidence(mark) or res.needs_confirmation or not res.resolved:
            item.uncertain = True
        items.append(item)

    proc = planned_procedure or read.planned_procedure
    kwargs = dict(
        items=items,
        is_laboratory_request=read.is_laboratory_request,
        planned_procedure=proc,
        procedure_source="slip" if proc else "unknown",
    )
    if synthetic:
        return RequestSlip.synthetic(**kwargs)
    return RequestSlip(image_sha256=image_sha256, redacted=True, **kwargs)


def triage(slip: RequestSlip) -> dict:
    """Split a slip into the buckets the waterfall expects.

    Returns {priceable, needs_confirmation, cancelled}. `priceable` is items we are
    confident enough to look up; whether MMC actually publishes a price for them is the
    pricing layer's problem, and unpriced ones land in `unpriced[]` there.
    """
    priceable: list[ExtractedItem] = []
    needs_confirmation: list[ExtractedItem] = []
    cancelled: list[ExtractedItem] = []

    for item in slip.items:
        if item.is_cancelled:
            cancelled.append(item)          # never priced, whatever it resolved to
        elif item.test_code is None or item.uncertain:
            needs_confirmation.append(item)
        else:
            priceable.append(item)

    return {
        "priceable": priceable,
        "needs_confirmation": needs_confirmation,
        "cancelled": cancelled,
    }


def read_and_extract(reader, image_path: Path, *, synthetic: bool = False) -> RequestSlip:
    """Convenience path used by the benchmark: reader -> slip, redaction included."""
    from vision.redact import load_and_redact

    red = load_and_redact(Path(image_path), synthetic=synthetic)
    result = reader.read(Path(image_path))
    return extract_request(result, red.sha256, synthetic=synthetic)
