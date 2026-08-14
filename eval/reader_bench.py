"""Reader benchmark: the RRL table (capstone spec #14, §6.3).

Scores a reader end to end -- image -> marks -> resolved codes -- against the gold set,
broken down by media class, because that is the axis the dataset was built to separate on.

Three metrics, and the third is the one that matters most here:

  recall     of the tests the doctor ordered, how many did we find?
  precision  of the tests we reported, how many were actually ordered?
  INVENTED   tests we reported that were never marked. Every one of these is a line on a
             patient's bill for a test nobody ordered, so it is reported as a raw count,
             not folded into precision where a good recall can hide it.

Plus the two traps the dataset grades directly: cancelled rows must not be billed, and a
document that is not a request must be recognised as such.

    python -m eval.reader_bench --limit 25
    python -m eval.reader_bench --reader oracle
"""

import argparse
import collections
import json
import random
from pathlib import Path

from vision.resolve import resolve

_ROOT = Path(__file__).resolve().parent.parent
BUDGET_SECONDS = 20.0          # plan §0.2, fixed before any measurement


def dataset_dir() -> Path:
    for d in sorted(_ROOT.glob("labrequests-*/labrequests")):
        return d
    raise FileNotFoundError("labrequests dataset not found")


def load_index() -> list[dict]:
    gt = dataset_dir() / "groundtruth"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gt.glob("*.json"))]


def stratified(samples: list[dict], limit: int, seed: int = 20260815) -> list[dict]:
    """Even coverage across media classes, so a score is not an accident of sampling."""
    by_class: dict[str, list[dict]] = collections.defaultdict(list)
    for s in samples:
        by_class[s.get("media_class", "?")].append(s)
    rng = random.Random(seed)
    for v in by_class.values():
        rng.shuffle(v)

    out: list[dict] = []
    classes = sorted(by_class)
    i = 0
    while len(out) < min(limit, len(samples)):
        bucket = by_class[classes[i % len(classes)]]
        if bucket:
            out.append(bucket.pop())
        i += 1
        if all(not b for b in by_class.values()):
            break
    return out


def codes_from(read) -> tuple[set[str], set[str]]:
    """Resolve a reader's marks into (ordered_codes, cancelled_codes)."""
    ordered, cancelled = set(), set()
    for m in read.marks:
        r = resolve(m.label, m.section)
        if not r.test_code:
            continue
        (cancelled if m.cancelled else ordered).add(r.test_code)
    return ordered, cancelled


def score(reader, samples: list[dict]) -> dict:
    per_class: dict[str, dict] = collections.defaultdict(
        lambda: {"tp": 0, "fn": 0, "invented": 0, "n": 0, "seconds": []}
    )
    totals = {"tp": 0, "fn": 0, "invented": 0}
    cancelled_ok = cancelled_total = 0
    nonlab_ok = nonlab_total = 0
    blank_ok = blank_total = 0
    errors: list[str] = []
    seconds: list[float] = []
    base = dataset_dir()

    for s in samples:
        img = base / "media" / Path(s["image"]).name
        if not img.exists():
            errors.append(f"{s['sample_id']}: image missing")
            continue

        read = reader.read(img)
        if not read.ok:
            errors.append(f"{s['sample_id']}: {read.error}")
            continue
        seconds.append(read.seconds)

        expected = set(s["expected"]["codes"])
        expected_cancelled = set(s["expected"].get("cancelled", []))
        got, got_cancelled = codes_from(read)

        tp = len(expected & got)
        fn = len(expected - got)
        invented = len(got - expected)

        cls = s.get("media_class", "?")
        pc = per_class[cls]
        pc["tp"] += tp; pc["fn"] += fn; pc["invented"] += invented; pc["n"] += 1
        pc["seconds"].append(read.seconds)
        totals["tp"] += tp; totals["fn"] += fn; totals["invented"] += invented

        # A cancelled row billed is the failure that costs a patient money.
        if expected_cancelled:
            cancelled_total += len(expected_cancelled)
            cancelled_ok += len(expected_cancelled - got)

        if s.get("kind") == "nonlab":
            nonlab_total += 1
            nonlab_ok += int(read.is_laboratory_request is False and not got)
        if s.get("kind") == "blank":
            blank_total += 1
            blank_ok += int(not got)

    tp, fn, inv = totals["tp"], totals["fn"], totals["invented"]
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + inv) if (tp + inv) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "reader": reader.name,
        "samples": len(samples),
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "invented": inv,
        "cancelled_not_billed": (cancelled_ok, cancelled_total),
        "nonlab_detected": (nonlab_ok, nonlab_total),
        "blank_empty": (blank_ok, blank_total),
        "seconds_mean": sum(seconds) / len(seconds) if seconds else 0.0,
        "seconds_max": max(seconds) if seconds else 0.0,
        "per_class": {k: dict(v) for k, v in per_class.items()},
        "errors": errors,
    }


def report(r: dict) -> None:
    print(f"\n=== {r['reader']}   n={r['samples']}")
    print(f"  recall     {r['recall']:.1%}")
    print(f"  precision  {r['precision']:.1%}")
    print(f"  F1         {r['f1']:.1%}")
    print(f"  INVENTED   {r['invented']}   <- tests reported that were never ordered")
    ok, tot = r["cancelled_not_billed"]
    print(f"  cancelled not billed  {ok}/{tot}")
    ok, tot = r["nonlab_detected"]
    print(f"  non-lab detected      {ok}/{tot}")
    ok, tot = r["blank_empty"]
    print(f"  blank -> empty        {ok}/{tot}")
    verdict = "within" if r["seconds_max"] <= BUDGET_SECONDS else "OVER"
    print(f"  latency    mean {r['seconds_mean']:.1f}s  max {r['seconds_max']:.1f}s "
          f"({verdict} the {BUDGET_SECONDS:.0f}s budget)")

    if r["per_class"]:
        print("\n  by media class (the axis the dataset separates on):")
        for cls in sorted(r["per_class"]):
            c = r["per_class"][cls]
            denom = c["tp"] + c["fn"]
            rec = c["tp"] / denom if denom else 0.0
            sec = sum(c["seconds"]) / len(c["seconds"]) if c["seconds"] else 0.0
            print(f"    {cls:16} n={c['n']:3}  recall {rec:6.1%}  invented {c['invented']:4}  "
                  f"{sec:5.1f}s")
    if r["errors"]:
        print(f"\n  errors ({len(r['errors'])}): {r['errors'][:5]}")


def build_reader(name: str, model: str | None):
    if name == "oracle":
        from vision.reader import OracleReader
        return OracleReader(dataset_dir() / "groundtruth")
    if name == "vlm":
        from vision.readers.vlm import VLMReader
        return VLMReader(model=model)
    raise SystemExit(f"unknown reader {name!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader", default="vlm", choices=["vlm", "oracle"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    samples = stratified(load_index(), args.limit)
    r = score(build_reader(args.reader, args.model), samples)
    report(r)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
