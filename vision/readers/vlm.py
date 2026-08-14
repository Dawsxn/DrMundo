"""Vision-LLM reader: the model looks at the form and says which rows are marked.

This is the arm that can actually do the task. A pure OCR pass reads every printed label
on the page whether or not it was ticked -- it has no concept of a mark -- so the question
"which tests did the doctor order" is not an OCR question at all. See
`vision/readers/ocr.py` for the measured version of that claim.

The prompt is doing real work and each instruction earns its place:

  - Ask for the SECTION HEADING with every label. Measured worth: 3.2% of labels
    (eval/resolver_bench.py ablation). Bare "KUB" appears under both Ultrasound and X-Ray
    on the same sheet and is otherwise unresolvable.
  - Ask for struck-through rows SEPARATELY. A cancelled test billed is worse than a test
    missed, because the patient pays for something they were told not to have.
  - Ask whether the page is a request at all. A lab RESULT report is covered in test names
    and reference ranges and is still not an order.
  - Return the label VERBATIM. Resolution to a code happens in vision/resolve.py against
    the taxonomy's alias table; a model paraphrasing "Stool Exam" into "Fecalysis" would
    hide whether the alias path works.
"""

import base64
import json
from pathlib import Path
from typing import Optional

from config import get_openai_client
from vision.reader import ReadMark, ReadResult, timed

SYSTEM = """You read Philippine laboratory request forms and report exactly which tests \
the doctor ordered.

Return ONLY JSON:
{
  "is_laboratory_request": true|false,
  "planned_procedure": string|null,
  "ordered": [{"label": "...", "section": "...", "uncertain": true|false}],
  "cancelled": [{"label": "...", "section": "..."}]
}

Rules:
- "ordered" lists ONLY rows with a mark: a tick, cross, filled box, slash, or a circle \
round the box or the label. A mark may overflow its box.
- A row that is STRUCK THROUGH or crossed out is CANCELLED, not ordered. Put it in \
"cancelled" and leave it out of "ordered". This matters: billing a cancelled test charges \
someone for a test their doctor withdrew.
- Copy each label VERBATIM as printed. Do not expand abbreviations, do not correct \
spelling, do not translate.
- Always give the SECTION HEADING the row appears under, exactly as printed (e.g. \
"Ultrasound", "X-Ray", "Cardiac Markers:"). Some labels are ambiguous without it.
- Set "uncertain": true when a mark is faint, partial, or you are unsure it is a mark.
- If NOTHING is marked, return empty lists. Do not invent plausible tests.
- If the page is not a laboratory REQUEST (for example a results report, prescription, \
referral, or medical certificate), set "is_laboratory_request": false and return empty \
lists. A results report lists test names and values but is not an order.
- "planned_procedure" is an operation named on the form, if any. Usually null."""


def _encode(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


class VLMReader:
    """Reads a form with a multimodal LLM."""

    # NOT config.CHAT_MODEL. gpt-4o-mini is the app's chat model and is measurably
    # unusable here: on a clean form it returned 24 tests where 7 were ordered, reading
    # every printed label rather than the marked ones. Mark detection is a capability
    # threshold, not a prompting problem -- see eval/reader_bench.py.
    DEFAULT_MODEL = "gpt-4.1"

    def __init__(self, model: Optional[str] = None, detail: str = "high") -> None:
        self.model = model or self.DEFAULT_MODEL
        self.detail = detail
        self.name = f"vlm:{self.model}"

    def read(self, image_path: Path) -> ReadResult:
        path = Path(image_path)
        try:
            with timed() as t:
                client = get_openai_client()
                resp = client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Which tests are ordered on this form?"},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{_encode(path)}",
                                        "detail": self.detail,
                                    },
                                },
                            ],
                        },
                    ],
                )
            payload = json.loads(resp.choices[0].message.content)
        except Exception as exc:                     # network, quota, malformed JSON
            return ReadResult(reader=self.name, error=f"{type(exc).__name__}: {exc}")

        marks = [
            ReadMark(
                label=m.get("label", ""),
                section=m.get("section"),
                cancelled=False,
                uncertain=bool(m.get("uncertain")),
            )
            for m in payload.get("ordered", []) or []
            if m.get("label")
        ]
        marks += [
            ReadMark(label=m.get("label", ""), section=m.get("section"), cancelled=True)
            for m in payload.get("cancelled", []) or []
            if m.get("label")
        ]

        return ReadResult(
            marks=marks,
            is_laboratory_request=bool(payload.get("is_laboratory_request", True)),
            planned_procedure=payload.get("planned_procedure") or None,
            seconds=t.seconds,
            reader=self.name,
        )
