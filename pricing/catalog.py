"""Bridge: a resolved test_code -> a priced MMC catalogue row.

The dataset names tests; MMC names services; nobody publishes a mapping between them.
This is the join, and it is deliberately the thinnest possible one: match on the
taxonomy's canonical name and its aliases against `hospital_prices.service`, and when
nothing matches, say so.

80 of the taxonomy's 87 codes reach a real MMC service. The rest fall into two groups and
the difference matters:

  ALIAS GAPS -- MMC calls it something else (TROPONIN_I is "TROPONIN I HIGH SENSITIVITY").
  Fixable, and fixed here through `CODE_TO_MMC`.

  GENUINE ABSENCES -- MMC publishes no price at all. Bone scan, inguinoscrotal ultrasound,
  biophysical profile, fecalysis. These are `unpriced[]`, which is the honest outcome and
  not a bug to engineer around (handoff §2).
"""

import re
from decimal import Decimal
from functools import lru_cache
from typing import Optional

from db.connection import get_connection
from pricing.schemas import PricedItem
from vision.resolve import _index as _taxonomy_index
from vision.schemas import ExtractedItem

# Hand-checked alias gaps: taxonomy code -> the exact MMC service name.
# Every one of these was verified against the rebuilt catalogue. Where MMC offers several
# variants the choice is recorded in the comment, because picking silently is how you end
# up quoting the wrong test.
CODE_TO_MMC: dict[str, str] = {
    "TROPONIN_I": "TROPONIN I HIGH SENSITIVITY",     # not the ER/POCT variants
    "CA_TOTAL": "CALCIUM SERUM",                      # not ionised, not 24h urine
    "ELECTROLYTES": "ELECTROLYTE PANEL",
    "US_BREAST": "BREAST ULTRASOUND/ELASTOGRAPHY",
    "OGTT_75G": "GLUCOSE TOLERANCE 2 SAMPLES 75 GRAMS (OGTT)",   # cheaper of two 75g
    "OGTT_100G": "GLUCOSE TOLERANCE 3 SAMPLES 100 GRAMS (OGTT)",  # cheaper of two 100g
    "FBS": "GLUCOSE (FBS/FPG)",
    "PPBS_2HR": "GLUCOSE 2HRS PPBS",
    "TSH": "TSH CHEMI",                    # chemiluminescence is MMC's routine assay
    "FT3": "FT3 CHEMI",
    "FT4": "FT4 CHEMI",
    "LDH": "LDH SERUM",                    # not the body-fluid assay
    "CPK_TOTAL": "CPK/CK",
    "HBSAG_SCREENING": "HBsAG",
    "PREGNANCY_TEST_SERUM": "PREGNANCY TEST",
    "PREGNANCY_TEST_URINE": "PREGNANCY TEST",   # MMC lists one test, not two
    "CBC_PLT": "CBC (COMPLETE BLOOD COUNT)",    # MMC's CBC already reports platelets
    "US_HBT": "HEPATOBILIARY/LIVER; GALLBLADDER; PANCREAS; SPLEEN",
}

# Codes MMC genuinely does not price. Listed so an unpriced result is a KNOWN gap rather
# than an unexplained miss -- the report says "MMC publishes no price", not "we failed".
KNOWN_UNPRICED: set[str] = {
    "FECALYSIS",
    "NM_BONE_SCAN",
    "US_INGUINOSCROTAL",
    "US_BPS",
    "PLATELET_COUNT",     # MMC prices it only inside CBC, not standalone
    "BUN",                # MMC publishes no standalone blood urea nitrogen
    "VLDL",               # calculated from a lipid profile, never billed alone
    "BILI_INDIRECT",      # MMC prices total and direct; indirect is derived from them
    "HBSAG_TITER",        # MMC lists screening only, no titre
    # AP *and Lateral*. MMC prices CHEST AP and CHEST LATERAL VIEW ONLY as separate
    # rows and publishes no combined AP&L. Quoting CHEST AP alone would silently drop
    # the lateral view and understate the bill, so this is reported unpriced instead.
    "XR_CHEST_AP_L",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


@lru_cache(maxsize=1)
def _service_index() -> dict[str, dict]:
    conn = get_connection()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT service, category, price_low, price_high, as_of, mmc_code "
            "FROM hospital_prices"
        )]
    finally:
        conn.close()
    return {_norm(r["service"]): r for r in rows}


def _candidate_names(code: str) -> list[str]:
    """Names worth trying for a code: the explicit mapping first, then the taxonomy's."""
    names: list[str] = []
    if code in CODE_TO_MMC:
        names.append(CODE_TO_MMC[code])
    entry = _taxonomy_index()["by_code"].get(code)
    if entry:
        names.append(entry["canonical_name"])
        names += entry.get("surface_forms", []) or []
        names += (entry.get("aliases", {}) or {}).get("global", []) or []
    return names


# MMC prices several variants of nearly every test. An outpatient request slip wants the
# plain one, so these are penalised rather than excluded -- excluded would lose the test
# entirely when only a variant exists.
_ER_MARKERS = ("er ", "poct", "point of care", "stat ")
_SPECIMEN_MISMATCH = {
    "blood": ("urine", "body fluid", "csf", "stool", "tissue"),
    "urine": ("serum", "body fluid", "csf", "stool"),
}


def _rank(service: str, specimen: str) -> tuple:
    """Lower is better. Order of the tuple IS the priority order.

    1. ER / POCT variants are emergency and point-of-care pricing; a request slip is
       neither, and quoting ER pricing overstates an outpatient bill.
    2. A blood test must not match a urine or body-fluid assay of the same analyte.
       CREATININE SERUM and CREATININE URINE 24HRS are different tests at different
       prices, and the slip says which.
    3. Shortest name wins: "CHEST PA" over "CHEST PA & LATERAL & APICOLORDOTIC". An
       unqualified order should get the unqualified service, not a richer one.
    """
    low = service.lower()
    is_er = any(m in low for m in _ER_MARKERS)
    mismatch = any(w in low for w in _SPECIMEN_MISMATCH.get(specimen, ()))
    return (is_er, mismatch, len(service))


def find_price(code: str) -> Optional[dict]:
    """The MMC row for a taxonomy code, or None when MMC publishes no price."""
    if not code:
        return None
    idx = _service_index()
    entry = _taxonomy_index()["by_code"].get(code) or {}
    specimen = (entry.get("specimen") or "").lower()

    # 1. Exact name match wins outright.
    for name in _candidate_names(code):
        row = idx.get(_norm(name))
        if row:
            return row

    # 2. Otherwise rank the token-aligned candidates and take the best.
    best = None
    for name in _candidate_names(code):
        key = _norm(name)
        if len(key) < 4:
            continue                       # "CL", "K", "MG" would match everything
        for row in idx.values():
            if not _aligns(key, row["service"]):
                continue
            r = _rank(row["service"], specimen)
            if best is None or r < best[0]:
                best = (r, row)
    return best[1] if best else None


def _aligns(key: str, service: str) -> bool:
    """Does `key` match `service` starting at a WORD boundary?

    Raw substring matching on normalised text is how CREATININE, whose surface form is
    "Crea", matched PANCREAS: "crea" sits inside "pan-crea-s". The shortest-name rule then
    preferred the 8-character PANCREAS over CREATININE SERUM, and a P740 blood test was
    priced as a P16,800 study. The taxonomy says `substring_matching: false` for exactly
    this reason.

    So the key must begin at a token boundary. Tokens are still joined afterwards, because
    MMC punctuates inconsistently and "Chest PA/L" has to reach "CHEST PA & LATERAL".
    """
    tokens = re.findall(r"[a-z0-9]+", service.lower())
    return any("".join(tokens[i:]).startswith(key) for i in range(len(tokens)))


def _is_exact(code: Optional[str], row: dict) -> bool:
    return any(_norm(n) == _norm(row["service"]) for n in _candidate_names(code or ""))


def price_item(item: ExtractedItem) -> Optional[PricedItem]:
    """Turn an extracted item into a priced one, or None if MMC publishes no price."""
    row = find_price(item.test_code or "")
    if row is None:
        return None
    return PricedItem(
        item=item,
        mmc_code=row["mmc_code"] or "",
        catalog_name=row["service"],
        price_low=Decimal(str(row["price_low"])),
        price_high=Decimal(str(row["price_high"])),
        # 1.0 only for a hand-verified mapping or an exact name hit; ranked matches
        # picked a variant and should read as slightly less certain.
        match_confidence=1.0 if _is_exact(item.test_code, row) else 0.85,
        as_of=row["as_of"],
    )


def price_items(items: list[ExtractedItem]) -> tuple[list[PricedItem], list[ExtractedItem]]:
    """Split extracted items into (priced, unpriced). Nothing is dropped."""
    priced: list[PricedItem] = []
    unpriced: list[ExtractedItem] = []
    for item in items:
        p = price_item(item)
        (priced.append(p) if p else unpriced.append(item))
    return priced, unpriced


def coverage_report() -> dict:
    """How much of the taxonomy MMC actually prices. Used by the eval suite."""
    codes = list(_taxonomy_index()["by_code"])
    priced = [c for c in codes if find_price(c) is not None]
    missing = [c for c in codes if c not in priced]
    return {
        "codes": len(codes),
        "priced": len(priced),
        "unpriced": sorted(missing),
        "known_unpriced": sorted(KNOWN_UNPRICED),
        "unexplained": sorted(set(missing) - KNOWN_UNPRICED),
    }
