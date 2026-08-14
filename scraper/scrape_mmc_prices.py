"""Extract Makati Medical Center's published price list into a raw CSV.

MMC publishes an official, searchable price list at https://www.makatimed.net.ph/price-list/
Each search is a plain form POST (`search=<term>`) and the response HTML already contains
every matching item AND its Low/High price -- embedded in a per-row inline <script> that
builds the "See Price" modal. So one request per search term yields fully-priced rows; no
per-item clicking and no API token are required.

This is a ONE-TIME BUILD STEP, exactly like scrape_case_rates.py. The app itself never does
live lookups -- it reads only the local SQLite DB built from the committed CSVs.

Every row carries MMC's own item code, which is the provenance anchor: any price in the
final dataset can be traced back to an official catalogue entry and re-checked by hand.

Usage:
    python scraper/scrape_mmc_prices.py                     # full sweep
    python scraper/scrape_mmc_prices.py --terms CBC LIPID   # ad-hoc lookup
"""

import argparse
import csv
import html as html_mod
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# The repo path can contain non-Latin characters, which breaks the default Windows console
# codec on print. Force UTF-8 output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://www.makatimed.net.ph/price-list/"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "data" / "mmc_price_list_raw.csv"
DELAY_SECONDS = 1.0  # be a polite client

# Search terms, grouped by the three scope categories. The site matches on substrings of the
# item name, so terms are chosen to sweep each category broadly rather than to name every
# item. Overlap between terms is fine -- rows are de-duplicated by MMC item code.
SEARCH_TERMS: dict[str, list[str]] = {
    "radiologic": [
        "X-RAY", "XRAY", "ULTRASOUND", "CT SCAN", "TOMOGRAPHY", "MRI",
        "MAGNETIC RESONANCE", "MAMMOGRAM", "MAMMOGRAPHY", "DOPPLER", "FLUOROSCOPY",
        "BONE DENSITOMETRY", "BONE MINERAL", "ECHOCARDIOGRAM", "2D ECHO", "ANGIOGRAM",
        "ANGIOGRAPHY", "SCINTIGRAPHY", "NUCLEAR", "PET", "CONTRAST", "RADIOGRAPH",
    ],
    "blood_test": [
        "CBC", "COMPLETE BLOOD", "HEMOGLOBIN", "HEMATOCRIT", "PLATELET", "RETICULOCYTE",
        "GLUCOSE", "FBS", "OGTT", "HBA1C", "GLYCOSYLATED",
        "CHOLESTEROL", "HDL", "LDL", "TRIGLYCERIDE", "LIPID", "LIPOPROTEIN",
        "CREATININE", "BUN", "UREA", "URIC ACID",
        "SGPT", "SGOT", "ALKALINE PHOSPHATASE", "BILIRUBIN", "ALBUMIN", "TOTAL PROTEIN",
        "SODIUM", "POTASSIUM", "CHLORIDE", "CALCIUM", "MAGNESIUM", "PHOSPHORUS",
        "ELECTROLYTE", "URINALYSIS", "FECALYSIS", "STOOL", "OCCULT BLOOD",
        "PROTHROMBIN", "APTT", "CLOTTING", "ESR", "CRP", "PROCALCITONIN",
        "TSH", "THYROID", "FT3", "FT4", "HEPATITIS", "HIV", "DENGUE", "TYPHIDOT",
        "CULTURE", "SEROLOGY", "PREGNANCY TEST", "PSA", "FERRITIN", "IRON",
        "VITAMIN D", "BLOOD TYPING", "PROFILE", "PANEL", "PACKAGE",
    ],
    # Facility rates are per-day and are NOT folded into any estimate -- length of stay is
    # unknowable from a doctor's request, and assuming one would invent the single largest
    # driver of the total. They are captured so the report can show them as a separate,
    # clearly-labelled line ("if admitted, room & board is billed separately at ...").
    "facility": [
        "ROOM AND BOARD", "SUITE", "WARD", "PRIVATE ROOM", "ISOLATION", "ICU",
        "INTENSIVE CARE", "CRITICAL CARE", "NURSERY", "OBSERVATION",
    ],
    "procedure": [
        "APPENDECTOMY", "CHOLECYSTECTOMY", "HERNIORRHAPHY", "HERNIOPLASTY",
        "DELIVERY", "CESAREAN", "CAESAREAN", "HYSTERECTOMY", "THYROIDECTOMY",
        "MASTECTOMY", "ARTHROPLASTY", "TONSILLECTOMY", "ADENOIDECTOMY",
        "CATARACT", "PHACOEMULSIFICATION", "BIOPSY", "ENDOSCOPY", "COLONOSCOPY",
        "GASTROSCOPY", "CIRCUMCISION", "LAPAROSCOPY", "LAPAROTOMY",
        "CRANIOTOMY", "THORACOTOMY", "MASTOIDECTOMY", "SEPTOPLASTY",
        "PROSTATECTOMY", "NEPHRECTOMY", "AMPUTATION", "FRACTURE",
    ],
}

# NOTE: rows can't be split on <tr>...</tr>. Each row's inline script embeds the modal's
# own HTML table as a string, so a non-greedy </tr> match terminates inside that string and
# truncates the row before its prices. Anchor on the "See Price" button instead: the item's
# visible cells sit just before it, and the modal (with the prices) just after it.
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_CODE_RE = re.compile(r'name="submitPrice"[^>]*value="([^"]+)"', re.I)
# Inside the inline script, the modal table's cells hold: name, generic, low, high.
_MODAL_CELL_RE = re.compile(r"<td class='text-left'>(.*?)</td>", re.S | re.I)
_ASOF_RE = re.compile(r"As of\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})", re.I)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(raw: str) -> str:
    """Strip tags/entities and collapse whitespace."""
    return re.sub(r"\s+", " ", html_mod.unescape(_TAG_RE.sub("", raw))).strip()


def _money(token: str) -> int | None:
    """'PHP 4,450.00' -> 4450. Returns None if the token isn't a peso amount."""
    m = re.search(r"([\d,]+)(?:\.\d{2})?", token.replace("PHP", "").strip())
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def fetch(term: str) -> str:
    data = urllib.parse.urlencode({"search": term}).encode()
    req = urllib.request.Request(
        URL,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace")


def parse(page: str) -> list[dict]:
    """Pull every priced catalogue row out of a search-results page."""
    items = []
    for button in _CODE_RE.finditer(page):
        # Visible cells: between the previous row's closing </script> and this button, so a
        # neighbouring row's embedded modal table can't leak into this row's cells.
        prev = page.rfind("</script>", 0, button.start())
        before = page[(prev + len("</script>")) if prev != -1 else 0: button.start()]
        tds = _TD_RE.findall(before)
        if len(tds) < 3:
            continue
        name, generic, mmc_type = (_clean(tds[-3]), _clean(tds[-2]), _clean(tds[-1]))

        # Prices: inside this row's own script, which builds the "See Price" modal.
        script_end = page.find("</script>", button.end())
        after = page[button.end(): script_end if script_end != -1 else button.end() + 6000]
        cells = [_clean(c) for c in _MODAL_CELL_RE.findall(after)]
        money = [c for c in cells if "PHP" in c.upper()]
        low = _money(money[0]) if money else None
        high = _money(money[1]) if len(money) >= 2 else low
        if low is None:
            continue  # no usable price -> not a row we can ground anything on

        asof_m = _ASOF_RE.search(after)
        items.append({
            "mmc_code": button.group(1),
            "name": name,
            "generic_name": generic,
            "mmc_type": mmc_type,
            "price_low": low,
            "price_high": high,
            "as_of": asof_m.group(1) if asof_m else "",
        })
    return items


def sweep(terms_by_category: dict[str, list[str]]) -> list[dict]:
    """Run every search term, de-duplicating by MMC item code."""
    found: dict[str, dict] = {}
    total_terms = sum(len(v) for v in terms_by_category.values())
    done = 0
    for category, terms in terms_by_category.items():
        for term in terms:
            done += 1
            try:
                rows = parse(fetch(term))
            except Exception as exc:  # noqa: BLE001 - keep sweeping, report at the end
                print(f"  [{done}/{total_terms}] {term!r} FAILED: {exc}")
                continue
            new = 0
            for row in rows:
                code = row["mmc_code"]
                if code in found:
                    # Same item reachable from several terms; record them all.
                    found[code]["matched_terms"] += f";{term}"
                else:
                    row["matched_terms"] = term
                    row["search_category"] = category
                    found[code] = row
                    new += 1
            print(f"  [{done}/{total_terms}] {term!r}: {len(rows)} rows ({new} new)")
            time.sleep(DELAY_SECONDS)
    return list(found.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape the MakatiMed published price list.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--terms", nargs="*", help="Ad-hoc search terms (skips the full sweep).")
    args = ap.parse_args()

    terms = {"adhoc": args.terms} if args.terms else SEARCH_TERMS
    print(f"Sweeping {sum(len(v) for v in terms.values())} search terms...")
    items = sweep(terms)
    items.sort(key=lambda r: (r["mmc_type"], r["name"]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["mmc_code", "name", "generic_name", "mmc_type", "price_low", "price_high",
              "as_of", "search_category", "matched_terms"]
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(items)

    print(f"\nWrote {len(items)} unique items to {args.output}")
    types: dict[str, int] = {}
    for it in items:
        types[it["mmc_type"]] = types.get(it["mmc_type"], 0) + 1
    print("\nItems by MMC type:")
    for t, n in sorted(types.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  {t or '(blank)'}")


if __name__ == "__main__":
    main()
