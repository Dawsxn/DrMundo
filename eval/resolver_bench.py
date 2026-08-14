"""Resolver benchmark against the gold set, with a PERFECT reader.

Runs every printed label in the 260 ground-truth files through `vision/resolve.py` and
compares the resulting code to the code the generator actually printed. No model is
involved: the reader is an oracle that returns exactly what is on the page.

That makes this an UPPER BOUND. Whatever a real vision LLM or OCR pass scores later, it
cannot exceed these numbers, because every failure here is a resolver failure that no
amount of reading accuracy will fix. Run it before spending anything on a model.

    python -m eval.resolver_bench
"""

import collections
import json
from pathlib import Path

from vision.resolve import resolve

_ROOT = Path(__file__).resolve().parent.parent


def dataset_dir() -> Path:
    for d in sorted(_ROOT.glob("labrequests-*/labrequests")):
        return d
    raise FileNotFoundError("labrequests dataset not found next to the repo root")


def load_samples() -> list[dict]:
    gt = dataset_dir() / "groundtruth"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gt.glob("*.json"))]


def run(use_sections: bool = True) -> dict:
    samples = load_samples()

    total = correct = wrong = ambiguous = unresolved = 0
    by_method: collections.Counter = collections.Counter()
    failures: list[tuple[str, str, str, str]] = []   # (sample, label, expected, got)
    cancelled_seen = 0

    for s in samples:
        for mark in s.get("marks", []):
            # A cancelled row must never be priced, but it still has to RESOLVE -- the
            # report names it, and naming it wrong is its own error.
            if mark.get("state") == "cancelled":
                cancelled_seen += 1

            label = mark.get("label_text_on_form")
            if not label:
                continue
            expected = mark["code"]
            got = resolve(label, mark.get("section") if use_sections else None)
            by_method[got.method] += 1
            total += 1

            if got.test_code == expected:
                correct += 1
            elif got.method == "ambiguous":
                ambiguous += 1
                failures.append((s["sample_id"], label, expected, f"ambiguous{got.candidates}"))
            elif got.test_code is None:
                unresolved += 1
                failures.append((s["sample_id"], label, expected, "unresolved"))
            else:
                wrong += 1
                failures.append((s["sample_id"], label, expected, got.test_code))

    return {
        "samples": len(samples),
        "labels": total,
        "correct": correct,
        "wrong": wrong,
        "ambiguous": ambiguous,
        "unresolved": unresolved,
        "cancelled_marks": cancelled_seen,
        "by_method": dict(by_method),
        "failures": failures,
    }


def main() -> None:
    r = run()
    n = r["labels"] or 1
    print(f"samples            {r['samples']}")
    print(f"labels resolved    {r['labels']}")
    print(f"  correct          {r['correct']:5}  ({r['correct'] / n:.1%})")
    print(f"  WRONG code       {r['wrong']:5}  ({r['wrong'] / n:.1%})   <- the dangerous one")
    print(f"  ambiguous        {r['ambiguous']:5}  ({r['ambiguous'] / n:.1%})   -> asks, does not guess")
    print(f"  unresolved       {r['unresolved']:5}  ({r['unresolved'] / n:.1%})")
    print(f"cancelled marks    {r['cancelled_marks']}")
    print(f"\nby method: {r['by_method']}")

    # Ablation: withhold the section heading. The dataset README warns that bare "KUB"
    # appears under both Ultrasound and X-Ray; this measures how much the heading is
    # actually worth, and what the failure looks like without it.
    a = run(use_sections=False)
    an = a["labels"] or 1
    print(f"\nWITHOUT section headings: {a['correct']}/{a['labels']} ({a['correct'] / an:.1%})")
    print(f"  became ambiguous {a['ambiguous']}, became WRONG {a['wrong']}")
    print("  -> headings are load-bearing, and their absence degrades to 'ask', not to a "
          "wrong code.")

    if r["failures"]:
        print(f"\nfirst 25 of {len(r['failures'])} failures:")
        for sid, label, expected, got in r["failures"][:25]:
            print(f"  {sid}  {label!r:34} expected {expected:22} got {got}")

        worst = collections.Counter(
            (label, expected, got) for _, label, expected, got in r["failures"]
        )
        print("\nmost common failures:")
        for (label, expected, got), count in worst.most_common(12):
            print(f"  {count:4}x  {label!r:30} expected {expected:20} got {got}")


if __name__ == "__main__":
    main()
