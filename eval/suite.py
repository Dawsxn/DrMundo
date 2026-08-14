"""The Scope v2 evaluation suite (plan §9, capstone spec criterion 3).

Answers one question with numbers rather than adjectives:

    Can an agent estimate the budget a patient needs to prepare, given only images of a
    doctor's request, accounting for both PhilHealth and HMO coverage?

Five layers, deliberately separated so a failure points at one stage:

    unit         the waterfall's arithmetic, and the item-accounting invariant
    component    reading (image -> labels) and matching (label -> priced catalogue row)
    trajectory   does the agent ask instead of guessing when it is unsure?
    end-to-end   hallucinated-peso rate: every figure in prose present in the structure
    judge        an honesty rubric an LLM scores (eval/judge.py)

The three headline numbers for the deck are OCR F1, top-1 match accuracy, and the
hallucinated-peso rate.

    python -m eval.suite --limit 25          # includes the VLM arm (costs API calls)
    python -m eval.suite --offline           # oracle reader only, free and deterministic
"""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from agent.format import format_budget_answer
from agent.schemas import Answer
from eval.reader_bench import BUDGET_SECONDS, dataset_dir, load_index, score, stratified
from eval.resolver_bench import run as resolver_run
from guardrails.output_guard import check_output
from pricing.catalog import coverage_report, price_items
from pricing.estimate import estimate_from_slip
from pricing.hmo import resolve_hmo_plan
from vision.extract_request import read_and_extract, triage
from vision.reader import OracleReader
from vision.resolve import resolve


# ------------------------------------------------------------------ component: matching
def match_accuracy() -> dict:
    """Top-1 accuracy of label -> priced catalogue row, with reading held perfect.

    Separated from reading on purpose: a wrong price and a missed test are different
    failures with different owners, and a combined number hides which one moved.
    """
    hit = miss_unpriced = miss_unresolved = 0
    unpriced_codes: dict[str, int] = {}

    for sample in load_index():
        for mark in sample.get("marks", []):
            label = mark.get("label_text_on_form")
            if not label or mark.get("state") == "cancelled":
                continue
            res = resolve(label, mark.get("section"))
            if not res.test_code:
                miss_unresolved += 1
                continue
            from pricing.catalog import find_price
            if find_price(res.test_code) is not None:
                hit += 1
            else:
                miss_unpriced += 1
                unpriced_codes[res.test_code] = unpriced_codes.get(res.test_code, 0) + 1

    total = hit + miss_unpriced + miss_unresolved
    return {
        "labels": total,
        "priced": hit,
        "accuracy": hit / total if total else 0.0,
        "unresolved": miss_unresolved,
        "no_mmc_price": miss_unpriced,
        "top_unpriced": sorted(unpriced_codes.items(), key=lambda kv: -kv[1])[:8],
    }


# ------------------------------------------------------------------ end-to-end: grounding
def hallucinated_peso_rate(limit: int = 40) -> dict:
    """Fraction of generated reports containing a peso figure absent from the structure.

    Target is zero. This is the trust metric: a number on a patient's screen that ties to
    nothing retrievable is the failure this whole project is built to prevent.
    """
    base = dataset_dir()
    reader = OracleReader(base / "groundtruth")
    checked = violations = 0
    offenders: list[str] = []

    for sample in load_index()[:limit]:
        img = base / "media" / Path(sample["image"]).name
        if not img.exists():
            continue
        slip = read_and_extract(reader, img, synthetic=True)
        est = estimate_from_slip(
            slip,
            hmo=resolve_hmo_plan("Maxicare", "Gold", remaining_balance=Decimal("40000")),
            senior_or_pwd=True,
        )
        answer = Answer(status="answered", path="budget_report",
                        query="slip", answer_text="", budget=est)
        answer.answer_text = format_budget_answer(answer)
        _, report = check_output(answer)
        checked += 1
        if not report.grounded:
            violations += 1
            offenders.append(f"{sample['sample_id']}: {report.violations[:4]}")

    return {
        "reports": checked,
        "ungrounded": violations,
        "rate": violations / checked if checked else 0.0,
        "offenders": offenders[:5],
    }


# ------------------------------------------------------------------ trajectory
def asks_instead_of_guessing() -> dict:
    """When a label is genuinely ambiguous, does it ask rather than price something?

    Uses the taxonomy's own blocked abbreviations. Bare "PT" is prothrombin time or a
    pregnancy test; pricing either is a coin flip with a patient's money.
    """
    from vision.reader import ReadMark, ReadResult
    from vision.extract_request import extract_request

    probes = ["PT", "CT", "BT", "KUB", "Chest"]
    asked = priced_anyway = 0
    for label in probes:
        slip = extract_request(ReadResult(marks=[ReadMark(label=label)], reader="probe"),
                               "h", synthetic=True)
        buckets = triage(slip)
        if buckets["needs_confirmation"]:
            asked += 1
        if buckets["priceable"]:
            priced_anyway += 1

    return {
        "ambiguous_probes": len(probes),
        "asked": asked,
        "priced_anyway": priced_anyway,
        "rate": asked / len(probes),
    }


def cancelled_never_billed(limit: int = 60) -> dict:
    """Struck-through rows must never reach a price. The failure that costs money."""
    base = dataset_dir()
    reader = OracleReader(base / "groundtruth")
    seen = billed = 0

    for sample in load_index():
        if not sample["expected"].get("cancelled"):
            continue
        if seen >= limit:
            break
        img = base / "media" / Path(sample["image"]).name
        if not img.exists():
            continue
        slip = read_and_extract(reader, img, synthetic=True)
        est = estimate_from_slip(slip)
        cancelled_codes = set(sample["expected"]["cancelled"])
        priced_codes = {p.item.test_code for p in est.priced}
        seen += len(cancelled_codes)
        billed += len(cancelled_codes & priced_codes)

    return {"cancelled_rows": seen, "billed": billed,
            "rate": billed / seen if seen else 0.0}


# ------------------------------------------------------------------ runner
def run_all(limit: int = 25, offline: bool = True, model: str | None = None) -> dict:
    resolver = resolver_run()
    resolver_no_section = resolver_run(use_sections=False)

    reader_scores = {}
    samples = stratified(load_index(), limit)
    if offline:
        reader_scores["oracle"] = score(OracleReader(dataset_dir() / "groundtruth"), samples)
    else:
        from vision.readers.vlm import VLMReader
        reader_scores["oracle"] = score(OracleReader(dataset_dir() / "groundtruth"), samples)
        reader_scores["vlm"] = score(VLMReader(model=model), samples)

    return {
        "resolver": {
            "labels": resolver["labels"],
            "correct": resolver["correct"],
            "accuracy": resolver["correct"] / resolver["labels"],
            "without_sections": resolver_no_section["correct"] / resolver_no_section["labels"],
            "wrong_without_sections": resolver_no_section["wrong"],
        },
        "matching": match_accuracy(),
        "catalogue": coverage_report(),
        "readers": reader_scores,
        "grounding": hallucinated_peso_rate(),
        "trajectory": asks_instead_of_guessing(),
        "cancelled": cancelled_never_billed(),
    }


def report(r: dict) -> None:
    print("=" * 74)
    print("DR. MUNDO -- SCOPE V2 EVALUATION")
    print("=" * 74)

    print("\nHEADLINE (the three numbers for the deck)")
    vlm = r["readers"].get("vlm")
    if vlm:
        print(f"  OCR/VLM F1                 {vlm['f1']:.1%}   ({vlm['reader']}, n={vlm['samples']})")
    else:
        print("  OCR/VLM F1                 not run (offline mode)")
    print(f"  top-1 match accuracy       {r['matching']['accuracy']:.1%}")
    print(f"  hallucinated-peso rate     {r['grounding']['rate']:.1%}   "
          f"({r['grounding']['ungrounded']}/{r['grounding']['reports']} reports)")

    print("\nCOMPONENT: resolution (label -> code), reading held perfect")
    res = r["resolver"]
    print(f"  {res['correct']}/{res['labels']} correct ({res['accuracy']:.1%})")
    print(f"  without section headings: {res['without_sections']:.1%}, "
          f"{res['wrong_without_sections']} wrong")

    print("\nCOMPONENT: matching (code -> priced MMC row)")
    m = r["matching"]
    print(f"  {m['priced']}/{m['labels']} priced ({m['accuracy']:.1%})")
    print(f"  unresolved {m['unresolved']} | MMC publishes no price {m['no_mmc_price']}")
    c = r["catalogue"]
    print(f"  catalogue coverage {c['priced']}/{c['codes']} codes, "
          f"{len(c['unexplained'])} unexplained")

    print("\nCOMPONENT: reading (image -> labels)")
    for name, s in r["readers"].items():
        verdict = "within" if s["seconds_max"] <= BUDGET_SECONDS else "OVER"
        print(f"  {name:8} recall {s['recall']:6.1%}  precision {s['precision']:6.1%}  "
              f"F1 {s['f1']:6.1%}  invented {s['invented']:3}  "
              f"max {s['seconds_max']:.1f}s ({verdict})")
        for cls in sorted(s["per_class"]):
            pc = s["per_class"][cls]
            denom = pc["tp"] + pc["fn"]
            print(f"      {cls:16} recall {pc['tp'] / denom if denom else 0:6.1%}  "
                  f"invented {pc['invented']}")

    print("\nSAFETY")
    t = r["trajectory"]
    print(f"  asks on ambiguity          {t['asked']}/{t['ambiguous_probes']} "
          f"(priced anyway: {t['priced_anyway']})")
    ca = r["cancelled"]
    print(f"  cancelled rows billed      {ca['billed']}/{ca['cancelled_rows']} "
          f"({ca['rate']:.1%})")

    print("\nLIMITATIONS, stated rather than buried")
    print("  - Every image is SYNTHETIC. There is no real-slip arm, so these numbers do")
    print("    not measure performance on a phone photo of a real request.")
    print("  - Every form is a LAB request. No form names a procedure, so the PhilHealth")
    print("    leg is never exercised from an image; it fires from the conversation.")
    print("  - HMO figures come from published individual/family tiers. Most PH coverage")
    print("    is employer-negotiated and will match no public tier.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--offline", action="store_true",
                    help="Skip the VLM arm. Free and deterministic.")
    ap.add_argument("--model", default=None)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    r = run_all(limit=args.limit, offline=args.offline, model=args.model)
    report(r)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
