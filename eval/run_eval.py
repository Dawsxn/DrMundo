"""Offline eval harness for Dr. Mundo (Phase 9b).

Runs the dataset through `DrMundoService.handle` and reports catalog-match accuracy, path
routing (A vs B), coverage/OOP correctness, refusal + clarification correctness, latency,
and token cost. Supports a prompt-variant ablation.

    # from repo root (needs OPENAI_API_KEY in .env):
    python -m eval.run_eval                     # baseline prompt (system_v1)
    python -m eval.run_eval --ablation          # system_v1 vs v2 vs v3, side by side
    python -m eval.run_eval --prompts system_v1,system_v2
    python -m eval.run_eval --limit 5           # quick subset while iterating
    python -m eval.run_eval --mlflow            # also log each case as an MLflow run

MLflow logging is OFF by default here so the suite is fast and repeatable; the same
token/cost plumbing that feeds MLflow feeds this report either way.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Allow running as a plain script (python eval/run_eval.py) as well as `-m eval.run_eval`.
_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if hasattr(sys.stdout, "reconfigure"):  # non-Latin repo paths break the default codec
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent.service import DrMundoService  # noqa: E402
from eval.scoring import CHECK_ORDER, case_passed, score_case, summarize  # noqa: E402

DATASET = pathlib.Path(__file__).resolve().parent / "dataset.json"


def load_cases(limit: int | None = None) -> list[dict]:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    return cases[:limit] if limit else cases


def run_prompt(prompt_name: str, cases: list[dict], enable_mlflow: bool) -> list[dict]:
    """Run every case under one prompt variant, returning per-case records."""
    svc = DrMundoService(prompt_name=prompt_name, enable_mlflow=enable_mlflow)
    records: list[dict] = []
    for case in cases:
        # Unique session per case+prompt so short-term memory never leaks across cases.
        session = f"eval::{prompt_name}::{case['id']}"
        try:
            result = svc.handle(case["question"], session_id=session)
            answer = result.answer
            checks = score_case(case, answer, result.category)
            records.append({
                "id": case["id"],
                "bucket": case["bucket"],
                "checks": checks,
                "passed": case_passed(checks),
                "latency_ms": result.latency_ms,
                "total_tokens": result.usage.total_tokens,
                "cost_usd": result.estimated_cost_usd,
                "status": answer.status,
                "path": answer.path,
                "category": result.category,
                "error": None,
            })
        except Exception as exc:  # noqa: BLE001 - a crashed case is a failed case
            records.append({
                "id": case["id"], "bucket": case["bucket"], "checks": {}, "passed": False,
                "latency_ms": 0, "total_tokens": 0, "cost_usd": 0.0,
                "status": "ERROR", "path": None, "category": "?", "error": str(exc),
            })
    return records


def print_case_table(prompt_name: str, records: list[dict]) -> None:
    print(f"\n=== Prompt: {prompt_name} — per case ===")
    print(f"{'result':6}  {'bucket':11}  {'id':30}  detail")
    for r in records:
        mark = "PASS" if r["passed"] else "FAIL"
        if r["error"]:
            detail = f"ERROR: {r['error'][:60]}"
        else:
            failed = [k for k in CHECK_ORDER if k in r["checks"] and not r["checks"][k]]
            detail = ("failed: " + ", ".join(failed)) if failed else f"{r['status']}/{r['path']}"
        print(f"{mark:6}  {r['bucket']:11}  {r['id']:30}  {detail}")


def print_summary(prompt_name: str, s: dict) -> None:
    def pct(x):
        return "  n/a" if x is None else f"{x * 100:5.1f}%"

    print(f"\n--- Prompt: {prompt_name} — summary ---")
    print(f"  overall pass:          {s['passed']}/{s['n']}  ({pct(s['pass_rate'])})")
    print(f"  routing accuracy:      {pct(s['routing_accuracy'])}   (Path A vs B)")
    print(f"  catalog match:         {pct(s['match_accuracy'])}")
    print(f"  coverage/OOP correct:  {pct(s['coverage_oop_accuracy'])}")
    print(f"  refusal accuracy:      {pct(s['refusal_accuracy'])}")
    print(f"  clarification acc.:    {pct(s['clarification_accuracy'])}")
    print("  pass by bucket:        " + "  ".join(
        f"{b}={pct(v)}" for b, v in sorted(s["bucket_pass_rate"].items())))
    print(f"  latency avg / p95:     {s['avg_latency_ms']:.0f} ms / {s['p95_latency_ms']:.0f} ms")
    print(f"  tokens / est. cost:    {s['total_tokens']:,}  /  ${s['total_cost_usd']:.4f}")


def print_ablation(summaries: dict[str, dict]) -> None:
    print("\n================= ABLATION (prompt comparison) =================")
    header = f"{'prompt':12}  {'pass':>7}  {'route':>6}  {'match':>6}  {'cov/oop':>7}  " \
             f"{'refuse':>6}  {'clarify':>7}  {'lat(ms)':>8}  {'cost($)':>8}"
    print(header)
    print("-" * len(header))

    def pct(x):
        return "n/a" if x is None else f"{x * 100:.0f}%"

    for name, s in summaries.items():
        print(f"{name:12}  {pct(s['pass_rate']):>7}  {pct(s['routing_accuracy']):>6}  "
              f"{pct(s['match_accuracy']):>6}  {pct(s['coverage_oop_accuracy']):>7}  "
              f"{pct(s['refusal_accuracy']):>6}  {pct(s['clarification_accuracy']):>7}  "
              f"{s['avg_latency_ms']:>8.0f}  {s['total_cost_usd']:>8.4f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Dr. Mundo offline eval harness")
    ap.add_argument("--prompts", default="system_v1",
                    help="comma-separated prompt names (default: system_v1)")
    ap.add_argument("--ablation", action="store_true",
                    help="shortcut for --prompts system_v1,system_v2,system_v3")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N cases")
    ap.add_argument("--mlflow", action="store_true",
                    help="also log each case as an MLflow run (off by default)")
    args = ap.parse_args()

    prompts = ["system_v1", "system_v2", "system_v3"] if args.ablation else \
        [p.strip() for p in args.prompts.split(",") if p.strip()]
    cases = load_cases(args.limit)
    print(f"Running {len(cases)} cases x {len(prompts)} prompt(s): {', '.join(prompts)}")

    summaries: dict[str, dict] = {}
    for prompt in prompts:
        records = run_prompt(prompt, cases, enable_mlflow=args.mlflow)
        print_case_table(prompt, records)
        s = summarize(records)
        summaries[prompt] = s
        print_summary(prompt, s)

    if len(prompts) > 1:
        print_ablation(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
