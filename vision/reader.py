"""Readers: image -> labelled marks. One interface, several implementations.

A reader's only job is to say WHAT IS ON THE PAGE. It does not resolve codes (that is
`vision/resolve.py`) and it certainly does not price anything. Keeping the boundary sharp
is what lets the RRL compare a vision LLM against local OCR on equal terms: both emit the
same `ReadResult`, and the same resolver and scorer run behind each.

Implementations live in `vision/readers/`. `OracleReader` is here because it is not a
candidate -- it reads ground truth rather than pixels, and exists to measure everything
downstream of reading with reading held perfect.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable


@dataclass
class ReadMark:
    """One item the reader believes is marked on the form."""

    label: str
    section: Optional[str] = None
    cancelled: bool = False
    uncertain: bool = False
    confidence: Optional[float] = None


@dataclass
class ReadResult:
    """Everything a reader has to say about one image."""

    marks: list[ReadMark] = field(default_factory=list)
    is_laboratory_request: bool = True
    planned_procedure: Optional[str] = None
    seconds: float = 0.0
    reader: str = "unknown"
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@runtime_checkable
class Reader(Protocol):
    """Anything that can turn an image path into a ReadResult."""

    name: str

    def read(self, image_path: Path) -> ReadResult: ...


class timed:
    """Context manager that records wall-clock seconds, for the latency budget.

    The budget (20s, plan §0.2) covers the whole chain, but the reader dominates it, so
    every reader reports its own time and the benchmark compares against the budget.
    """

    def __init__(self) -> None:
        self.seconds = 0.0

    def __enter__(self) -> "timed":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.seconds = time.perf_counter() - self._t0


class OracleReader:
    """Reads the ground truth, not the image. NOT a benchmark candidate.

    Establishes the ceiling: with reading held perfect, whatever the pipeline scores is
    the best it could ever do. Any candidate reader's score is bounded by it, so a gap
    between the two is attributable to reading and nothing else.
    """

    name = "oracle"

    def __init__(self, groundtruth_dir: Path) -> None:
        self.groundtruth_dir = Path(groundtruth_dir)

    def read(self, image_path: Path) -> ReadResult:
        import json

        sample_id = Path(image_path).stem.split("_")[0]
        gt_path = self.groundtruth_dir / f"{sample_id}.json"
        if not gt_path.exists():
            return ReadResult(reader=self.name, error=f"no ground truth for {sample_id}")

        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        marks = [
            ReadMark(
                label=m.get("label_text_on_form") or m["code"],
                section=m.get("section"),
                cancelled=m.get("state") == "cancelled",
                uncertain=bool(m.get("ambiguous")),
            )
            for m in gt.get("marks", [])
        ]
        return ReadResult(
            marks=marks,
            is_laboratory_request=gt.get("expected", {}).get("is_laboratory_request", True),
            reader=self.name,
        )
