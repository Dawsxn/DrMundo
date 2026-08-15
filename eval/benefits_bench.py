"""Benchmark for the benefits reader: does it read the limits, and does it invent any?

Two scores, and the second matters more than the first.

  RECALL      of the fields the document states, how many did we read correctly?
  FABRICATION of the fields the document does NOT state, how many did we fill in anyway?

A reader that scores 100% recall and fabricates one outpatient ceiling is worse than one
that scores 80% and fabricates nothing, because the fabricated figure is indistinguishable
from a real one by the time it reaches a patient. That is what the sparse HR one-pager
specimen is for: almost every field is absent, and every field filled in there is a
fabrication by definition.

Run:  python -m eval.benefits_bench
"""

import json
from decimal import Decimal
from pathlib import Path

SPECIMENS = Path(__file__).resolve().parent.parent / "data" / "benefits_specimens"

# Ground-truth key -> how to pull the same figure off an HMOPlan.
SCALARS = {
    "mbl_annual": lambda p: p.mbl_annual,
    "room_entitlement": lambda p: p.room_entitlement,
    "outpatient_diagnostics_limit": lambda p: p.outpatient_diagnostics_limit,
    "professional_fees_within_mbl": lambda p: p.professional_fees_within_mbl,
    "preexisting_first_year_limit": lambda p: p.preexisting_cap,
    "preexisting_dreaded_first_year_limit": lambda p: p.preexisting_cap,
    "default_procedure_sublimit": lambda p: p.default_procedure_sublimit,
}


def _same(expected, got) -> bool:
    """Compare a ground-truth value with what the reader produced.

    Numbers compare numerically, so Decimal("150000") and 150000 agree. Strings compare
    case- and space-insensitively, because "Semi - Private" and "Semi-Private" are the
    same room and a reader should not be marked wrong for the hyphen.
    """
    if expected is None or got is None:
        return expected is None and got is None
    if isinstance(expected, bool) or isinstance(got, bool):
        return bool(expected) == bool(got)
    if isinstance(expected, (int, float)) or isinstance(got, (Decimal, int, float)):
        try:
            return Decimal(str(expected)) == Decimal(str(got))
        except Exception:
            return False
    return "".join(str(expected).lower().split()) == "".join(str(got).lower().split())


def _expected_scalars(truth: dict, category: str = None,
                      category_key: str = None) -> dict:
    """Flatten a ground-truth entry to the fields a single HMOPlan should carry.

    A group contract states several sets of figures and a plan carries one, so anything
    recorded per category is resolved down to the category we asked the reader for.
    """
    out = {k: truth.get(k) for k in SCALARS if k in truth}
    for key, value in out.items():
        if isinstance(value, dict):
            out[key] = value.get(category_key) if category_key else None
    if category and truth.get("categories", {}).get(category):
        cat = truth["categories"][category]
        out["mbl_annual"] = cat.get("mbl_annual")
        out["room_entitlement"] = cat.get("room_entitlement")
    return out


def _expected_sublimits(truth: dict, category_key: str = None) -> dict:
    subs = truth.get("procedure_sublimits") or {}
    out = {}
    for name, value in subs.items():
        if isinstance(value, dict):
            if category_key and category_key in value:
                out[name] = value[category_key]
        else:
            out[name] = value
    return out


def _matched_sublimit(name: str, produced: dict):
    """Find the reader's cap for a ground-truth procedure name.

    The ground truth is keyed by canonical name and the reader copies the document's
    wording verbatim, so "MRI" has to reach "Magnetic Resonance Imaging (MRI)". Matching
    on shared words rather than equality, in one place, keeps that leniency visible.
    """
    from pricing.textmatch import norm

    target = norm(name)
    for key, amount in produced.items():
        k = norm(key)
        if target and (target in k or k in target):
            return amount
    return None


def run(verbose: bool = True) -> dict:
    from vision.benefits import read_benefits

    truths = json.loads((SPECIMENS / "groundtruth.json").read_text(encoding="utf-8"))
    totals = {"stated": 0, "read": 0, "absent": 0, "fabricated": 0,
              "sublimits_expected": 0, "sublimits_read": 0}
    rows = []

    for truth in truths:
        # The corporate specimen states three sets of figures; ask for the cheapest, which
        # is also the one a reader is most likely to confuse with the headline numbers.
        category = "Rank and File" if truth.get("categories") else None
        cat_key = "rank_and_file" if category else None

        result = read_benefits(SPECIMENS / truth["document"], member_category=category)
        if not result.ok:
            rows.append((truth["document"], f"ERROR {result.error}"))
            continue

        stated = read = absent = fabricated = 0
        for key, expected in _expected_scalars(truth, category, cat_key).items():
            got = SCALARS[key](result.plan)
            if expected is None:
                absent += 1
                fabricated += 0 if got is None else 1
                if verbose and got is not None:
                    print(f"    FABRICATED {key}: document says nothing, reader said {got}")
            else:
                stated += 1
                ok = _same(expected, got)
                read += 1 if ok else 0
                if verbose and not ok:
                    print(f"    MISSED {key}: expected {expected}, got {got}")

        expected_subs = _expected_sublimits(truth, cat_key)
        hits = sum(1 for n, v in expected_subs.items()
                   if _same(v, _matched_sublimit(n, result.plan.procedure_sublimits)))
        if truth.get("procedure_sublimits") is None and result.plan.procedure_sublimits:
            fabricated += len(result.plan.procedure_sublimits)

        for k, v in (("stated", stated), ("read", read), ("absent", absent),
                     ("fabricated", fabricated), ("sublimits_expected", len(expected_subs)),
                     ("sublimits_read", hits)):
            totals[k] += v

        rows.append((
            truth["document"],
            f"fields {read}/{stated}  sublimits {hits}/{len(expected_subs)}  "
            f"fabricated {fabricated}/{absent} absent  [{result.mode}, {result.seconds:.1f}s]"
        ))

    if verbose:
        print("\nBenefits reader benchmark")
        print("=" * 78)
        for name, line in rows:
            print(f"  {name:38} {line}")
        stated = totals["stated"] or 1
        subs = totals["sublimits_expected"] or 1
        print("-" * 78)
        print(f"  field recall     {totals['read']}/{totals['stated']} "
              f"({100 * totals['read'] / stated:.0f}%)")
        print(f"  sub-limit recall {totals['sublimits_read']}/{totals['sublimits_expected']} "
              f"({100 * totals['sublimits_read'] / subs:.0f}%)")
        print(f"  FABRICATED       {totals['fabricated']} "
              f"(of {totals['absent']} fields the documents leave unstated)")
    return totals


if __name__ == "__main__":
    run()
