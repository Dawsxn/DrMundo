"""Propose MMC-procedure -> PhilHealth RVS-code mappings for review.

MMC's price list uses its own item codes; PhilHealth pays by RVS code. Nothing publishes a
mapping between them, so the link has to be established deliberately. Getting it wrong is
the project's most dangerous failure mode: variants of the same operation can carry very
different case rates (cholecystectomy is P60,450 / P90,675 / P104,130 depending on the
code), and a wrong pick produces an out-of-pocket figure that *looks* fine while being tens
of thousands of pesos off.

So this script does not decide anything. It shortlists candidates with a transparent score
and flags how confident the match is, and the resulting CSV is reviewed by hand before any
mapping is committed to `data/mmc_rvs_crosswalk.csv`.

Scoring signals, in order of weight:
  1. Approach must agree. PhilHealth codes laparoscopic and open separately (47562 vs
     47600), and MMC names say which one ("LAPAROSCOPIC CHOLECYSTECTOMY"). Disagreeing on
     approach is disqualifying, not merely a penalty.
  2. The operative root word must appear (CHOLECYSTECTOMY, APPENDECTOMY, ...).
  3. Qualifier agreement (ruptured, with cholangiography, bilateral, ...).

Ties are broken toward the LOWER case rate, deliberately: a lower assumed PhilHealth benefit
yields a higher estimated out-of-pocket, so an ambiguous match errs toward over-preparing
the patient rather than under-quoting the bill.

Usage:
    python -m data.propose_rvs_crosswalk --input data/mmc_price_list_raw.csv
    python -m data.propose_rvs_crosswalk --name "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE"
"""

import argparse
import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RATES_CSV = ROOT / "data" / "procedure_case_rates.csv"
DEFAULT_RAW = ROOT / "data" / "mmc_price_list_raw.csv"
DEFAULT_OUT = ROOT / "data" / "mmc_rvs_crosswalk_proposed.csv"

# Words that carry no discriminating power in either catalogue.
STOP = {
    "PACKAGE", "SURGERY", "ANESTHESIOLOGY", "GENERAL", "W", "WITH", "AND", "OR", "THE",
    "OF", "ONLY", "EG", "E", "G", "ANY", "METHOD", "PROCEDURE", "SURGICAL", "PER",
}
LAP_MARKERS = {"LAPAROSCOPIC", "LAPAROSCOPY", "LAP"}
OPEN_MARKERS = {"OPEN"}
QUALIFIERS = {
    "RUPTURED", "BILATERAL", "UNILATERAL", "TOTAL", "SUBTOTAL",
    "PARTIAL", "RADICAL", "SIMPLE", "COMPLETE", "ABDOMINAL", "VAGINAL", "PRIMARY",
    "RECURRENT", "INCARCERATED", "STRANGULATED", "MODIFIED",
}
# Markers that a candidate bundles an EXTRA procedure the MMC item didn't mention. These are
# what separate e.g. 47562 "LAPAROSCOPY; CHOLECYSTECTOMY" (P60,450) from 47564 "...WITH
# EXPLORATION OF COMMON DUCT" (P90,675) -- same root word, P30k apart. Without this the two
# tie and the choice falls to a coin-flip.
#
# Deliberately NOT a blanket penalty on every unmatched word: PhilHealth descriptions are
# verbose elaborations of the same operation ("APPENDECTOMY; FOR RUPTURED APPENDIX W/ ABSCESS
# OR GENERALIZED PERITONITIS"), so penalising all extra tokens would wrongly demote the
# correct, more-specific match.
ADDITIVE_MARKERS = {
    "EXPLORATION", "CHOLANGIOGRAPHY", "RECONSTRUCTION", "REVISION", "GRAFT",
    "IMPLANT", "IMPLANTATION", "TRANSPLANT", "ANASTOMOSIS", "RESECTION",
}


def tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^A-Z0-9]+", text.upper()) if t and t not in STOP}


def approach(toks: set[str]) -> str | None:
    """'lap' | 'open' | None (unstated)."""
    if toks & LAP_MARKERS:
        return "lap"
    if toks & OPEN_MARKERS:
        return "open"
    return None


def root_words(toks: set[str]) -> set[str]:
    """Operative root words -- the surgical nouns that must agree.

    Approach markers are excluded: LAPAROSCOPY ends in -SCOPY but describes *how* the
    operation is done, not a second operation, and counting it as a root both mis-scores
    every laparoscopic candidate and prints a misleading reason.
    """
    return {t for t in toks if len(t) > 6 and t not in LAP_MARKERS and (
        t.endswith("ECTOMY") or t.endswith("OSTOMY") or t.endswith("OTOMY")
        or t.endswith("PLASTY") or t.endswith("RRHAPHY") or t.endswith("SCOPY")
        or t.endswith("CENTESIS") or t.endswith("PEXY")
    )}


def score(mmc_name: str, rvs_name: str) -> tuple[float, list[str]]:
    """Return (score, reasons). Score < 0 means disqualified."""
    a, b = tokens(mmc_name), tokens(rvs_name)
    reasons: list[str] = []

    ra, rb = root_words(a), root_words(b)
    if ra and rb:
        if ra & rb:
            reasons.append(f"root match: {'/'.join(sorted(ra & rb))}")
        else:
            return -1.0, ["different operation"]
    elif ra and not rb:
        return -1.0, ["target has no operative root"]

    app_a, app_b = approach(a), approach(b)
    if app_a and app_b and app_a != app_b:
        return -1.0, [f"approach mismatch ({app_a} vs {app_b})"]
    if app_a and app_a == app_b:
        reasons.append(f"approach agrees ({app_a})")
    # MMC says laparoscopic but the RVS entry is silent -> that entry is the open one.
    if app_a == "lap" and app_b is None:
        reasons.append("MMC is laparoscopic; candidate is unqualified (likely open)")

    qa, qb = a & QUALIFIERS, b & QUALIFIERS
    if qa & qb:
        reasons.append(f"qualifier match: {'/'.join(sorted(qa & qb))}")
    extra_qual = qb - qa
    if extra_qual:
        reasons.append(f"candidate adds: {'/'.join(sorted(extra_qual))}")

    # Extra bundled work the MMC item never mentioned -> almost certainly the wrong code.
    extra_add = (b & ADDITIVE_MARKERS) - a
    if extra_add:
        reasons.append(f"candidate bundles extra: {'/'.join(sorted(extra_add))}")
    # A second operative root means a second operation entirely.
    extra_roots = rb - ra
    if extra_roots:
        reasons.append(f"extra operation: {'/'.join(sorted(extra_roots))}")

    overlap = len(a & b)
    s = (overlap * 1.0 + len(ra & rb) * 3.0 + len(qa & qb) * 2.0
         - len(extra_qual) * 1.5 - len(extra_add) * 2.5 - len(extra_roots) * 3.0)
    if app_a and app_a == app_b:
        s += 3.0
    if app_a == "lap" and app_b is None:
        s -= 2.0
    return s, reasons


def load_rates() -> list[dict]:
    with RATES_CSV.open(encoding="utf-8") as f:
        return [{"rvs_code": r["rvs_code"], "procedure": r["procedure"],
                 "case_rate": float(r["case_rate"])} for r in csv.DictReader(f)]


def propose(mmc_name: str, rates: list[dict], top_k: int = 4) -> list[dict]:
    scored = []
    for r in rates:
        s, reasons = score(mmc_name, r["procedure"])
        if s > 0:
            scored.append({**r, "score": s, "why": "; ".join(reasons)})
    # Best score first; ties break toward the LOWER case rate (conservative -> higher OOP).
    scored.sort(key=lambda x: (-x["score"], x["case_rate"]))
    return scored[:top_k]


def confidence(cands: list[dict]) -> str:
    if not cands:
        return "none"
    if len(cands) == 1:
        return "high"
    top, second = cands[0], cands[1]
    if top["score"] - second["score"] >= 3.0:
        return "high"
    # Several candidates, but they all pay the same -> the choice cannot cost anything.
    if len({c["case_rate"] for c in cands}) == 1:
        return "high (rates identical)"
    return "REVIEW"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--name", help="Score a single name instead of a whole file.")
    ap.add_argument("--types", nargs="*", default=["OPERATING ROOM", "DELIVERY SURGERY"],
                    help="MMC types to map (these hold the hospital package prices).")
    args = ap.parse_args()

    rates = load_rates()

    if args.name:
        for c in propose(args.name, rates):
            print(f"  {c['rvs_code']}  P{c['case_rate']:>10,.2f}  score={c['score']:>5.1f}  "
                  f"{c['procedure'][:60]}")
            print(f"        why: {c['why']}")
        return

    wanted = set(args.types)
    with args.input.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["mmc_type"] in wanted]
    print(f"{len(rows)} hospital-package items to map, from {sorted(wanted)}\n")

    out = []
    for row in rows:
        cands = propose(row["name"], rates)
        conf = confidence(cands)
        best = cands[0] if cands else None
        out.append({
            "mmc_code": row["mmc_code"],
            "mmc_name": row["name"],
            "price_low": row["price_low"],
            "price_high": row["price_high"],
            "proposed_rvs": best["rvs_code"] if best else "",
            "proposed_procedure": best["procedure"] if best else "",
            "case_rate": f"{best['case_rate']:.2f}" if best else "",
            "confidence": conf,
            "why": best["why"] if best else "no candidate",
            "alternatives": " | ".join(
                f"{c['rvs_code']}=P{c['case_rate']:,.0f}" for c in cands[1:]),
        })
        flag = "" if conf.startswith("high") else "  <-- needs a decision"
        print(f"{conf:<20} {row['name'][:48]:<50} -> "
              f"{best['rvs_code'] if best else '(none)':<8}{flag}")

    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"\nWrote {len(out)} proposals to {args.output}")


if __name__ == "__main__":
    main()
