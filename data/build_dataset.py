"""Build the Scope v2 CSVs from the raw MakatiMed pull + the curated RVS crosswalk.

Everything written here traces to an official MMC catalogue item (`mmc_code`) or, for case
rates, to PhilHealth's published Annex B. Nothing is invented: an item with no published
price simply does not get a row, and the agent reports it as unpriced.

Output tables, and why they are separate:

  hospitals                  the single in-scope hospital (Makati Medical Center)
  hospital_procedure_prices  scope (a) -- procedures WITH a verified RVS code, so the
                             PhilHealth case rate can be applied
  hospital_prices            scope (b) radiologic + (c) blood tests, plus procedures whose
                             RVS code could not be honestly determined (they keep their real
                             price but carry no case rate)
  lab_panels                 panel -> member mapping, for "is the panel cheaper?" (scope c)
  professional_fees          surgeon / anaesthesiologist fees, published separately by MMC
  facility_rates             per-day room & board. DELIBERATELY ITS OWN TABLE: length of
                             stay is unknowable from a doctor's request, so these must never
                             be multiplied into a headline estimate. Keeping them out of the
                             priced tables makes that a structural guarantee rather than a
                             convention someone can forget.

Usage:
    python -m data.build_dataset
"""

import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "mmc_price_list_raw.csv"
CROSSWALK = DATA / "mmc_rvs_crosswalk.csv"

HOSPITAL_ID = 2
HOSPITAL_NAME = "Makati Medical Center"
HOSPITAL_CITY = "makati"
SOURCE = "mmc-price-list"

LAB_PREFIX = "LAB-"
IMAGING_TYPES = {"MRI", "RADIO CT", "RADIO ULTRASOUND", "RADIO DIAGNOSTICS",
                 "RADIO INTERVENTION", "RADIO PET IMAGING", "NUCLEAR MEDICINE",
                 "DR ULTRASOUND", "OSTEOPOROSIS & BONE HEALTH", "BREAST CLINIC"}
# Diagnostic studies that are neither imaging nor blood work (ECG, 2D echo, spirometry,
# endoscopy). Strictly these fall outside the three stated scope categories, but they appear
# constantly on real doctor's requests, so they are captured under their own category rather
# than being silently conflated with "radiologic studies".
DIAGNOSTIC_TYPES = {"CVDL - HEART STATION", "PULMONARY LABORATORY",
                    "NEUROVASCULAR LABORATORY", "CARDIAC CATH LAB", "ENDOSCOPY UNIT",
                    "E.N.T. DIAGNOSTIC CENTER", "CLS EYE CENTER", "NSDL"}
FACILITY_TYPES = {"ROOM AND BOARD", "CRITICAL CARE UNIT"}
PROF_FEE_TYPE = "CLINICAL SERVICES (PROF FEE)"
PACKAGE_TYPES = {"OPERATING ROOM", "DELIVERY SURGERY"}
# Imaging can also live under a clinic department (e.g. BREAST CLINIC / mammogram).
IMAGING_NAME_RE = re.compile(
    r"\b(ULTRASOUND|X-?RAY|MRI|CT SCAN|TOMOGRAPHY|MAMMOGRA|SONOGRA|DOPPLER|"
    r"FLUOROSCOP|ANGIOGRA|SCINTIGRA|RADIOGRAPH|DENSITOMETRY|PET)\b", re.I)
# Lines that are facility use / admin, not a clinical item you can be quoted for.
NON_ITEM_RE = re.compile(
    r"^(USE OF|ADDITIONAL USE OF)\b|\b(EXTRA COPY|KITTING|STAND ?BY|PER HOUR|SET-?UP)\b", re.I)

# Panel -> member test names, curated against what the pull actually contains. A panel is
# only listed when EVERY member exists as its own priced row, otherwise the "panel vs
# individual" comparison would be half-grounded and misleading.
LAB_PANELS: dict[str, list[str]] = {
    "LIPID PROFILE (HDL LDL CHOL TRIG) SERUM": [
        "CHOLESTEROL TOTAL SERUM", "HDL", "LDL", "TRIGLYCERIDES SERUM",
    ],
    "LIPID PROFILE (HDL LDL TRIG) SERUM": ["HDL", "LDL", "TRIGLYCERIDES SERUM"],
    "LIPID PROFILE (HDL & LDL) SERUM": ["HDL", "LDL"],
}


def money(v: str) -> int:
    return int(float(v))


def fmt(n: int) -> str:
    """Match the existing CSVs: thousands separators (quoting is csv's job)."""
    return f"{n:,}"


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name:<34} {len(rows):>5} rows")


def main() -> None:
    raw = list(csv.DictReader(RAW.open(encoding="utf-8")))
    cross = list(csv.DictReader(CROSSWALK.open(encoding="utf-8")))
    by_name = {r["name"]: r for r in raw}

    print("Building Scope v2 dataset from real MakatiMed data\n")

    # --- hospitals ---------------------------------------------------------------------
    write(DATA / "hospitals.csv", ["id", "hospital", "city"],
          [{"id": HOSPITAL_ID, "hospital": HOSPITAL_NAME, "city": HOSPITAL_CITY}])

    # --- scope (a): procedures with a verified RVS code --------------------------------
    proc_rows, unmapped_names = [], set()
    for c in cross:
        if c["rvs_code"]:
            proc_rows.append({
                "rvs_code": c["rvs_code"], "hospital_id": HOSPITAL_ID,
                "price_low": fmt(money(c["price_low"])),
                "price_high": fmt(money(c["price_high"])),
                "as_of": by_name[c["mmc_name"]]["as_of"],
                "mmc_code": c["mmc_code"], "source": SOURCE,
                "confidence": c["confidence"], "price_basis": c["price_basis"],
            })
        else:
            unmapped_names.add(c["mmc_name"])
    proc_rows.sort(key=lambda r: r["rvs_code"])
    write(DATA / "hospital_procedure_prices.csv",
          ["rvs_code", "hospital_id", "price_low", "price_high", "as_of", "mmc_code",
           "source", "confidence", "price_basis"], proc_rows)

    # --- scope (b) + (c) + unmapped procedures -----------------------------------------
    priced, next_id = [], 1
    for r in raw:
        t, name = r["mmc_type"], r["name"]
        if NON_ITEM_RE.search(name):
            continue
        if t.startswith(LAB_PREFIX):
            category = "Laboratory"
        elif t in IMAGING_TYPES or (t not in FACILITY_TYPES and t != PROF_FEE_TYPE
                                    and t not in PACKAGE_TYPES and IMAGING_NAME_RE.search(name)):
            category = "Imaging"
        elif t in DIAGNOSTIC_TYPES:
            category = "Diagnostic"
        elif name in unmapped_names:
            # A real procedure we could not tie to an RVS code: keep the published price,
            # but it lands here precisely because it has no case rate to apply.
            category = "Procedure (no case rate)"
        else:
            continue
        priced.append({
            "id": next_id, "hospital_id": HOSPITAL_ID, "category": category,
            "service": name, "price_low": fmt(money(r["price_low"])),
            "price_high": fmt(money(r["price_high"])), "as_of": r["as_of"],
            "mmc_code": r["mmc_code"], "source": SOURCE,
        })
        next_id += 1
    write(DATA / "hospital_prices.csv",
          ["id", "hospital_id", "category", "service", "price_low", "price_high", "as_of",
           "mmc_code", "source"], priced)

    # --- lab panels --------------------------------------------------------------------
    have = {p["service"] for p in priced}
    panel_rows, pid, skipped = [], 1, []
    for panel, members in LAB_PANELS.items():
        missing = [m for m in [panel, *members] if m not in have]
        if missing:
            skipped.append((panel, missing))
            continue
        for m in members:
            panel_rows.append({"id": pid, "panel_service": panel, "member_service": m})
            pid += 1
    write(DATA / "lab_panels.csv", ["id", "panel_service", "member_service"], panel_rows)
    for panel, missing in skipped:
        print(f"    ! panel skipped (members not priced): {panel} -> {missing}")

    # --- professional fees --------------------------------------------------------------
    pf, pf_id = [], 1
    for r in raw:
        if r["mmc_type"] != PROF_FEE_TYPE or NON_ITEM_RE.search(r["name"]):
            continue
        pf.append({"id": pf_id, "hospital_id": HOSPITAL_ID, "service": r["name"],
                   "price_low": fmt(money(r["price_low"])),
                   "price_high": fmt(money(r["price_high"])), "as_of": r["as_of"],
                   "mmc_code": r["mmc_code"], "source": SOURCE})
        pf_id += 1
    write(DATA / "professional_fees.csv",
          ["id", "hospital_id", "service", "price_low", "price_high", "as_of", "mmc_code",
           "source"], pf)

    # --- facility rates (per DAY -- never summed into an estimate) ----------------------
    fac, fid = [], 1
    for r in raw:
        if r["mmc_type"] not in FACILITY_TYPES or NON_ITEM_RE.search(r["name"]):
            continue
        fac.append({"id": fid, "hospital_id": HOSPITAL_ID, "room_type": r["name"],
                    "rate_low": fmt(money(r["price_low"])),
                    "rate_high": fmt(money(r["price_high"])), "unit": "per day",
                    "as_of": r["as_of"], "mmc_code": r["mmc_code"], "source": SOURCE})
        fid += 1
    write(DATA / "facility_rates.csv",
          ["id", "hospital_id", "room_type", "rate_low", "rate_high", "unit", "as_of",
           "mmc_code", "source"], fac)

    print(f"\nCategories in hospital_prices:")
    counts: dict[str, int] = {}
    for p in priced:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>5}  {k}")


if __name__ == "__main__":
    main()
