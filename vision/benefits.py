"""Reading a schedule of benefits: booklet or certificate -> the limits that bind.

The second document this project understands, and a different problem from the first. A
request slip asks "which rows are MARKED", which is a vision question no OCR pass can
answer. A benefits booklet asks "what do these figures MEAN", which is a reading-
comprehension question: the text is usually machine-readable, and the difficulty is that
"up to PhP15,000.00" appears eleven times on a page and each occurrence governs something
different.

So the strategy inverts. Text first, pixels only when there is no text:

  a born-digital PDF   ->  extract the text, read it with a chat model
  a scan or a photo    ->  render/encode to an image, read it with the vision model

The same reasoning that picked gpt-4.1 for slips applies here for the scanned path, and
for the text path the accuracy question is comprehension rather than perception.

WHAT THIS DELIBERATELY WILL NOT DO
Fill in a field the document does not state. An HR one-pager carries a plan name, a limit
and nothing else, and a reader that helpfully supplies "the usual" outpatient ceiling for
that tier produces a peso figure the patient will act on. Absent means null, and null
means we ask or we caveat. That is the whole reason the sparse specimen exists.
"""

import base64
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from config import get_openai_client
from pricing.schemas import HMOPlan
from vision.reader import timed

TEXT_MODEL = "gpt-4.1"
VISION_MODEL = "gpt-4.1"

# Below this many characters a PDF is a scan with a caption, not a text document, and the
# text path would read a page number and confidently return nothing.
MIN_TEXT_CHARS = 400

SYSTEM = """You read Philippine HMO benefit documents (Summary of Benefits, Certificate of \
Coverage, benefit booklets, HR advisories) and report the limits exactly as written.

Return ONLY JSON:
{
  "provider": string|null,
  "plan_name": string|null,
  "mbl": number|null,
  "mbl_basis": "per_illness_per_year"|"per_year"|null,
  "room_entitlement": string|null,
  "coverage_pct": number|null,
  "outpatient_diagnostics_limit": number|null,
  "professional_fees_within_mbl": true|false|null,
  "preexisting_pct_of_mbl": number|null,
  "preexisting_cap": number|null,
  "procedure_sublimits": [{"procedure": "...", "limit": number}],
  "exclusions": ["..."],
  "member_category": string|null
}

Rules:
- Report ONLY what the document states. If it does not say, use null and an empty list. \
Never fill a field with what a plan of that type usually carries. A number you supplied \
yourself will be shown to a patient as their coverage.
- "mbl" is the Maximum Benefit Limit, sometimes written MBL or Maximum Benefits Limit. If \
the document says it is per illness or per disease, set mbl_basis to \
"per_illness_per_year".
- "procedure_sublimits" comes from the Special Modalities and Procedures section, or any \
table giving a per-procedure cap ("Laparoscopic cholecystectomy - covered up to \
PhP15,000.00"). Copy the procedure name VERBATIM. Do not expand or translate it.
- A catch-all row such as "all other non-conventional but medically necessary procedures" \
belongs in procedure_sublimits with that wording kept.
- "coverage_pct" is only for a stated co-insurance or co-pay (80% reimbursement -> 0.8). \
Full cover, or no mention, is null and not 1.0.
- "professional_fees_within_mbl" is true when doctors' or surgeons' fees are listed as \
subject to, or charged against, the Maximum Benefit Limit.
- Amounts are numbers without separators: "PhP15,000.00" -> 15000.
- WHERE LIMITS DIFFER BY MEMBER CATEGORY, report the figures for the category named in \
the user's message. If none is named, report the LOWEST limits stated, because \
overstating a patient's coverage is the costlier error."""


@dataclass
class BenefitsResult:
    """What a reader has to say about one benefits document."""

    plan: Optional[HMOPlan] = None
    raw: dict = field(default_factory=dict)
    exclusions: list = field(default_factory=list)
    member_category: Optional[str] = None
    pages: int = 0
    mode: str = "unknown"          # "text" or "vision"
    seconds: float = 0.0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.plan is not None


class BenefitsUnreadable(RuntimeError):
    """The document could not be read. Never fall through to an empty plan.

    An empty HMOPlan is indistinguishable from "no coverage", and telling a member with a
    ₱150,000 limit to prepare the whole bill is a worse failure than saying so.
    """


def _pdf_text(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n\n".join(pages), len(pages)


def _pdf_page_images(path: Path, dpi: int = 150) -> list[bytes]:
    import fitz

    doc = fitz.open(str(path))
    try:
        return [page.get_pixmap(dpi=dpi).tobytes("png") for page in doc]
    finally:
        doc.close()


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _ask(messages: list) -> dict:
    resp = get_openai_client().chat.completions.create(
        model=TEXT_MODEL, temperature=0,
        response_format={"type": "json_object"}, messages=messages,
    )
    return json.loads(resp.choices[0].message.content)


def read_benefits(path, *, member_category: Optional[str] = None) -> BenefitsResult:
    """Read a benefits document into an HMOPlan. Text path first, vision as the fallback."""
    path = Path(path)
    suffix = path.suffix.lower()
    ask_for = (f"\n\nReport the figures for this member category: {member_category}."
               if member_category else "")

    try:
        with timed() as t:
            if suffix == ".pdf":
                text, pages = _pdf_text(path)
                if len(text.strip()) >= MIN_TEXT_CHARS:
                    mode = "text"
                    payload = _ask([
                        {"role": "system", "content": SYSTEM},
                        {"role": "user",
                         "content": f"Benefits document:{ask_for}\n\n{text[:60000]}"},
                    ])
                else:
                    mode = "vision"
                    payload = _ask(_vision_messages(_pdf_page_images(path), ask_for))
            else:
                mode, pages = "vision", 1
                payload = _ask(_vision_messages([path.read_bytes()], ask_for))
    except Exception as exc:                       # network, quota, malformed JSON, bad file
        return BenefitsResult(mode="unknown", error=f"{type(exc).__name__}: {exc}")

    return _to_result(payload, pages=pages if suffix == ".pdf" else 1,
                      mode=mode, seconds=t.seconds)


def _vision_messages(images: list, ask_for: str) -> list:
    content = [{"type": "text",
                "text": f"Read this benefits document.{ask_for}"}]
    for blob in images[:8]:                        # a booklet is long; the limits are early
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64.b64encode(blob).decode()}",
                          "detail": "high"},
        })
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def _to_result(payload: dict, *, pages: int, mode: str, seconds: float) -> BenefitsResult:
    """Payload -> HMOPlan, dropping anything that is not a usable figure.

    `mbl_source` is left as `uploaded_document` rather than `published_tier`, so the report
    stops telling the patient their figures came from a published tier that may not be
    theirs. It came from their own document, which is the strongest evidence we can have.
    """
    sublimits: dict[str, Decimal] = {}
    default_sublimit: Optional[Decimal] = None
    for row in payload.get("procedure_sublimits") or []:
        name = (row.get("procedure") or "").strip()
        amount = _to_decimal(row.get("limit"))
        if not name or amount is None:
            continue
        if _is_catch_all(name):
            default_sublimit = amount
        else:
            sublimits[name] = amount

    pct = payload.get("coverage_pct")
    plan = HMOPlan(
        provider=payload.get("provider") or None,
        plan_name=payload.get("plan_name") or None,
        mbl_annual=_to_decimal(payload.get("mbl")),
        room_entitlement=payload.get("room_entitlement") or None,
        coverage_pct=float(pct) if isinstance(pct, (int, float)) and 0 < pct <= 1 else 1.0,
        procedure_sublimits=sublimits,
        default_procedure_sublimit=default_sublimit,
        outpatient_diagnostics_limit=_to_decimal(payload.get("outpatient_diagnostics_limit")),
        preexisting_pct_of_mbl=_to_decimal(payload.get("preexisting_pct_of_mbl")),
        preexisting_cap=_to_decimal(payload.get("preexisting_cap")),
        professional_fees_within_mbl=payload.get("professional_fees_within_mbl"),
        exclusions=[e for e in (payload.get("exclusions") or []) if isinstance(e, str)],
        mbl_source="patient_stated" if payload.get("mbl") is not None else None,
        schedule_source="uploaded_document",
    )
    return BenefitsResult(
        plan=plan, raw=payload,
        exclusions=plan.exclusions,
        member_category=payload.get("member_category") or None,
        pages=pages, mode=mode, seconds=seconds,
    )


_CATCH_ALL_HINTS = ("all other", "non-conventional", "nonconventional", "any other")


def _is_catch_all(name: str) -> bool:
    """Is this the schedule's residual row rather than a named procedure?

    "All other non-conventional but medically necessary procedures" is not a procedure. Left
    in the named map it would never match anything and its cap would be lost; treated as the
    default it does what the schedule means.
    """
    low = name.lower()
    return any(h in low for h in _CATCH_ALL_HINTS)


def merge_into(plan: HMOPlan, existing: Optional[HMOPlan]) -> HMOPlan:
    """Fold a freshly read document into what the patient already told us.

    The patient's own figures win. A remaining balance is read off a member portal and is
    current; a booklet states the limit at issue and knows nothing about what has been
    claimed since. Nothing in the document may overwrite that.
    """
    if existing is None:
        return plan
    keep = {
        "remaining_balance": existing.remaining_balance,
        "preexisting": existing.preexisting,
        "accredited_at_mmc": existing.accredited_at_mmc,
        "covers_outpatient_diagnostics": existing.covers_outpatient_diagnostics,
    }
    merged = plan.model_copy(update={k: v for k, v in keep.items() if v is not None})
    # A cap the patient stated for a specific procedure is evidence too, and it should not
    # be dropped just because a booklet arrived afterwards without that procedure in it.
    for name, amount in existing.procedure_sublimits.items():
        merged.procedure_sublimits.setdefault(name, amount)
    return merged
