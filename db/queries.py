"""Parameterized, read-only SQL query functions -- the ONLY place SQL is written.

The LLM never generates SQL. It picks which of these typed functions to call and fills
their arguments; these functions run fixed, parameterized statements and return plain
dicts/lists. Every function returns a `status` so the agent can react instead of the
function raising:
    "ok"                  -> data found
    "no_data"             -> nothing matched (e.g. procedure not priced anywhere)
    "needs_clarification" -> ambiguous hospital name; `candidates` lists the options
"""

import csv
import sqlite3
from functools import lru_cache
from pathlib import Path

from db.aliases import equivalent_services
from db.connection import get_connection

_CROSSWALK = Path(__file__).resolve().parent.parent / "data" / "mmc_rvs_crosswalk.csv"


@lru_cache(maxsize=1)
def _package_names() -> dict:
    """mmc_code -> the package name MMC prints on its price list.

    Scope v2 has ONE hospital, so a procedure with several rows is not several hospitals,
    it is several packages: RVS 47562 is both "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE" and
    the "W/ ICG" version at P24,500 more. The name lives in the crosswalk rather than the
    price table, so it is read from there instead of widening the schema.
    """
    if not _CROSSWALK.exists():
        return {}
    with _CROSSWALK.open(encoding="utf-8") as fh:
        return {r["mmc_code"]: r["mmc_name"] for r in csv.DictReader(fh) if r.get("mmc_code")}


# --------------------------------------------------------------------------------------
# Hospital resolution + listing
# --------------------------------------------------------------------------------------
def list_hospitals(name_query: str | None = None, city: str | None = None) -> list[dict]:
    """Return hospitals, optionally filtered by case-insensitive substring on name/city."""
    conn = get_connection()
    sql = "SELECT id, hospital, city FROM hospitals"
    clauses, params = [], []
    if name_query:
        clauses.append("LOWER(hospital) LIKE ?")
        params.append(f"%{name_query.lower().strip()}%")
    if city:
        clauses.append("LOWER(city) LIKE ?")
        params.append(f"%{city.lower().strip()}%")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = [dict(r) for r in conn.execute(sql, params)]
    conn.close()
    return rows


def _resolve_hospital(conn: sqlite3.Connection, hospital) -> tuple[str, list[dict]]:
    """Resolve a hospital id or name to a single row.

    Returns (status, rows):
        ("ok", [row])         exactly one match
        ("multiple", rows)    name matched several -> caller asks user to pick
        ("none", [])          no match
    """
    if hospital is None:
        return "none", []

    # Numeric id (int or digit string)?
    if isinstance(hospital, int) or (isinstance(hospital, str) and hospital.strip().isdigit()):
        row = conn.execute(
            "SELECT id, hospital, city FROM hospitals WHERE id = ?", (int(hospital),)
        ).fetchone()
        return ("ok", [dict(row)]) if row else ("none", [])

    # Name substring (case-insensitive).
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT id, hospital, city FROM hospitals WHERE LOWER(hospital) LIKE ?",
            (f"%{hospital.lower().strip()}%",),
        )
    ]
    if len(rows) == 1:
        return "ok", rows
    if len(rows) > 1:
        return "multiple", rows
    return "none", []


# --------------------------------------------------------------------------------------
# Out-of-pocket math (Path A only) -- follows the spec's coverage rules exactly.
# --------------------------------------------------------------------------------------
def _compute_oop(case_rate: float, price_low: int, price_high: int, price_basis: str | None = None) -> dict:
    # A case rate is all-in for the episode. When it exceeds MMC's ceiling price, MMC
    # cannot be billing the whole episode -- the published figure is a COMPONENT charge,
    # and "fully covered" against it understates a real bill by thousands (handoff §5.4).
    # Out-of-pocket is genuinely uncomputable here: we do not know the rest of the bill.
    if price_basis == "component":
        return {
            "oop_low": None,
            "oop_high": None,
            "fully_covered": False,
            "coverage_note": "MMC's published figure covers only part of this procedure, so "
            "the actual bill will be higher. Out-of-pocket cannot be estimated from it.",
        }
    if case_rate >= price_high:
        return {
            "oop_low": 0.0,
            "oop_high": 0.0,
            "fully_covered": True,
            "coverage_note": "PhilHealth case rate meets or exceeds the price range -- "
            "this may be fully covered.",
        }
    if case_rate >= price_low:  # covers low end but not high end
        return {
            "oop_low": 0.0,
            "oop_high": float(price_high - case_rate),
            "fully_covered": False,
            "coverage_note": "May be fully covered at the low end of the price range; "
            "out-of-pocket grows toward the high end.",
        }
    return {
        "oop_low": float(price_low - case_rate),
        "oop_high": float(price_high - case_rate),
        "fully_covered": False,
        "coverage_note": "PhilHealth case rate is deducted from the hospital price.",
    }


# --------------------------------------------------------------------------------------
# PATH A: covered procedures
# --------------------------------------------------------------------------------------
def get_covered_cost(rvs_code: str, hospital=None) -> dict:
    """Case rate + hospital price + out-of-pocket for a covered procedure.

    If `hospital` is given -> that hospital's range + OOP.
    If not -> across-hospitals range + per-hospital breakdown + OOP on that range.
    Always includes the PhilHealth case rate (even when no hospital price exists).
    """
    conn = get_connection()
    try:
        proc = conn.execute(
            "SELECT rvs_code, procedure, case_rate FROM philhealth_procedure_rates WHERE rvs_code = ?",
            (str(rvs_code).strip(),),
        ).fetchone()
        if proc is None:
            return {"status": "no_data", "kind": "covered", "rvs_code": rvs_code,
                    "message": f"No covered procedure found for RVS code {rvs_code}."}
        proc = dict(proc)
        case_rate = proc["case_rate"]

        base = {
            "status": "ok",
            "kind": "covered",
            "rvs_code": proc["rvs_code"],
            "procedure": proc["procedure"],
            "case_rate": case_rate,
        }

        # Resolve a specific hospital if one was requested.
        target_hospital = None
        if hospital is not None:
            hstatus, hrows = _resolve_hospital(conn, hospital)
            if hstatus == "multiple":
                return {**base, "status": "needs_clarification",
                        "message": "Multiple hospitals match that name. Which one?",
                        "candidates": hrows}
            if hstatus == "none":
                return {**base, "status": "no_data",
                        "message": f"No hospital matches '{hospital}'.",
                        "hint": "Try list_hospitals to see available hospitals."}
            target_hospital = hrows[0]

        # Pull price rows (all hospitals, or just the resolved one).
        if target_hospital is not None:
            price_rows = conn.execute(
                "SELECT hpp.hospital_id, h.hospital, h.city, hpp.price_low, hpp.price_high, "
                "hpp.as_of, hpp.price_basis, hpp.confidence, hpp.mmc_code "
                "FROM hospital_procedure_prices hpp JOIN hospitals h ON h.id = hpp.hospital_id "
                "WHERE hpp.rvs_code = ? AND hpp.hospital_id = ?",
                (proc["rvs_code"], target_hospital["id"]),
            ).fetchall()
        else:
            price_rows = conn.execute(
                "SELECT hpp.hospital_id, h.hospital, h.city, hpp.price_low, hpp.price_high, "
                "hpp.as_of, hpp.price_basis, hpp.confidence, hpp.mmc_code "
                "FROM hospital_procedure_prices hpp JOIN hospitals h ON h.id = hpp.hospital_id "
                "WHERE hpp.rvs_code = ? ORDER BY hpp.price_low",
                (proc["rvs_code"],),
            ).fetchall()
        price_rows = [dict(r) for r in price_rows]

        # Covered by PhilHealth but no hospital price on file (the common 4,302 case, or
        # a specific hospital that doesn't list this procedure).
        if not price_rows:
            where = f" at {target_hospital['hospital']}" if target_hospital else ""
            return {**base, "status": "ok", "hospital": target_hospital,
                    "price_low": None, "price_high": None,
                    "message": f"PhilHealth case rate is P{case_rate:,.2f}, but we have no "
                               f"hospital price on file for this procedure{where}."}

        # Per-hospital breakdown with OOP each.
        breakdown = []
        for r in price_rows:
            oop = _compute_oop(case_rate, r["price_low"], r["price_high"], r["price_basis"])
            breakdown.append({
                "hospital_id": r["hospital_id"], "hospital": r["hospital"], "city": r["city"],
                "price_low": r["price_low"], "price_high": r["price_high"],
                "oop_low": oop["oop_low"], "oop_high": oop["oop_high"],
                "fully_covered": oop["fully_covered"],
                "price_basis": r["price_basis"], "confidence": r["confidence"],
                "mmc_code": r["mmc_code"],
                # What MMC calls this package, so several rows for one hospital read as
                # the variants they are rather than as a repeated hospital name.
                "package": _package_names().get(r["mmc_code"]),
            })

        price_low = min(r["price_low"] for r in price_rows)
        price_high = max(r["price_high"] for r in price_rows)

        # Aggregate conservatively: if ANY row is a component price, the aggregate cannot
        # be claimed as a whole-episode price either. Same for confidence -- the weakest
        # mapping in the set is what the caller should reason about.
        agg_basis = "component" if any(r["price_basis"] == "component" for r in price_rows) else "package"
        agg_conf = min(
            (r["confidence"] for r in price_rows),
            key=lambda c: {"high": 2, "medium": 1, "low": 0}.get(c, 0),
        )

        oop = _compute_oop(case_rate, price_low, price_high, agg_basis)
        as_of = price_rows[0]["as_of"]

        return {
            **base,
            "hospital": target_hospital,           # None -> across all hospitals
            "price_low": price_low,
            "price_high": price_high,
            **oop,
            "price_basis": agg_basis,
            "confidence": agg_conf,
            "hospitals": breakdown,
            "as_of": as_of,
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------------------
# PATH B: outpatient services (NOT PhilHealth-covered -> no case rate, no OOP)
# --------------------------------------------------------------------------------------
def get_outpatient_cost(service: str, hospital=None) -> dict:
    """Price range for an outpatient service. Aggregates equivalent service names across
    hospitals (see SERVICE_EQUIVALENTS) so the comparison covers every hospital."""
    conn = get_connection()
    try:
        members = equivalent_services(service)  # includes `service` itself
        placeholders = ",".join("?" for _ in members)

        target_hospital = None
        params = list(members)
        hospital_clause = ""
        if hospital is not None:
            hstatus, hrows = _resolve_hospital(conn, hospital)
            if hstatus == "multiple":
                return {"status": "needs_clarification", "kind": "outpatient",
                        "service": service,
                        "message": "Multiple hospitals match that name. Which one?",
                        "candidates": hrows}
            if hstatus == "none":
                return {"status": "no_data", "kind": "outpatient", "service": service,
                        "message": f"No hospital matches '{hospital}'."}
            target_hospital = hrows[0]
            hospital_clause = " AND hp.hospital_id = ?"
            params.append(target_hospital["id"])

        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT hp.hospital_id, h.hospital, h.city, hp.category, hp.service, "
                f"hp.price_low, hp.price_high, hp.as_of "
                f"FROM hospital_prices hp JOIN hospitals h ON h.id = hp.hospital_id "
                f"WHERE hp.service IN ({placeholders}){hospital_clause} "
                f"ORDER BY hp.price_low",
                params,
            )
        ]

        if not rows:
            where = f" at {target_hospital['hospital']}" if target_hospital else ""
            return {"status": "no_data", "kind": "outpatient", "service": service,
                    "message": f"No price on file for '{service}'{where}."}

        breakdown = [
            {"hospital_id": r["hospital_id"], "hospital": r["hospital"], "city": r["city"],
             "service": r["service"], "price_low": r["price_low"], "price_high": r["price_high"]}
            for r in rows
        ]
        return {
            "status": "ok",
            "kind": "outpatient",
            "service": service,
            "category": rows[0]["category"],
            "hospital": target_hospital,               # None -> across all hospitals
            "price_low": min(r["price_low"] for r in rows),
            "price_high": max(r["price_high"] for r in rows),
            "hospitals": breakdown,
            "as_of": rows[0]["as_of"],
            "philhealth_covered": False,
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------------------
# SCOPE V2: panels, professional fees, facility rates
# --------------------------------------------------------------------------------------

# `facility_rates` is NOT purely room & board despite its name -- it is MMC's whole
# per-day facility department. Without this split the UI would offer "CARDIOVERSION" and
# "RHYTHM STRIPS 6 SECONDS" (P31) as places to sleep.
#   room          elective accommodation -- what a patient actually chooses
#   critical_care a bed, but clinically assigned, never chosen from a menu
#   ancillary     equipment, procedures and fees that merely happen to bill per day
ROOM_TYPES = {
    "WARD", "SEMI PRIVATE", "SMALL PRIVATE", "LARGE PRIVATE", "PREMIUM LARGE PRIVATE",
    "HIGH RISK PRIVATE", "ISOLATION PRIVATE", "NEURO-PSYCHIATRY PRIVATE",
    "NEURO-PSYCHIATRY WARD", "RAI PRIVATE", "REGULAR SUITE", "PRESIDENTIAL SUITE",
    "OB ROOM WARD", "OB ROOM SEMI PRIVATE", "OB ROOM SMALL PRIVATE", "OB ROOM LARGE PRIVATE",
    "BMT POSITIVE PRESSURE", "HEALTH HUB PREMIER",
}
CRITICAL_CARE_TYPES = {
    "CARDIOVASCULAR ICU", "ICU SURGICAL/MEDICAL/NEURO", "ECMO ICU", "HEMODIAFILTRATION ICU",
    "NEONATAL ICU", "NICU ISOLATION", "PICU COMMON", "PICU SOLO",
}


def _facility_kind(room_type: str) -> str:
    if room_type in ROOM_TYPES:
        return "room"
    if room_type in CRITICAL_CARE_TYPES:
        return "critical_care"
    return "ancillary"


def get_facility_rates(kind: str | None = "room") -> dict:
    """Per-day facility rates. Defaults to elective accommodation only.

    These are ALWAYS a separate line and never summed into an estimate: length of stay
    is unknowable from a request slip, and assuming one invents the largest number on the
    page (handoff §8). Pass kind=None to get everything, including ancillary charges.
    """
    conn = get_connection()
    try:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT room_type, rate_low, rate_high, unit, as_of, mmc_code, source "
                "FROM facility_rates ORDER BY rate_low"
            )
        ]
        for r in rows:
            r["kind"] = _facility_kind(r["room_type"])
        if kind is not None:
            rows = [r for r in rows if r["kind"] == kind]
        if not rows:
            return {"status": "no_data", "kind_filter": kind, "rates": []}
        return {
            "status": "ok",
            "kind_filter": kind,
            "rates": rows,
            "cheapest": rows[0],
            "dearest": rows[-1],
            "unit": rows[0]["unit"],
            "never_in_total": True,   # structural reminder for callers (handoff §8)
        }
    finally:
        conn.close()


def get_professional_fees(service_query: str) -> dict:
    """Surgeon / anaesthesiologist fees matching a phrase.

    A separate line, excluded from the headline total by scope. Note the case rate also
    pays part of the doctor's fee, so never net a full case rate against a facility-only
    gross (plan §2.2).
    """
    q = (service_query or "").lower().strip()
    if not q:
        return {"status": "no_data", "query": service_query, "fees": []}
    conn = get_connection()
    try:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT service, price_low, price_high, as_of, mmc_code, source "
                "FROM professional_fees WHERE LOWER(service) LIKE ? ORDER BY price_low",
                (f"%{q}%",),
            )
        ]
        if not rows:
            return {"status": "no_data", "query": service_query, "fees": [],
                    "message": f"MMC publishes no professional fee matching '{service_query}'."}
        return {
            "status": "ok",
            "query": service_query,
            "fees": rows,
            "price_low": min(r["price_low"] for r in rows),
            "price_high": max(r["price_high"] for r in rows),
            "excluded_from_total": True,
        }
    finally:
        conn.close()


def get_panel_comparison(panel_service: str) -> dict:
    """Compare a lab panel's own price against the sum of its member tests.

    Returns `cheaper` = "panel" | "components" | None. If any member is unpriced the
    comparison is reported INCOMPLETE rather than summing the subset -- a partial sum
    understates the component side and makes the panel look better than it is.
    """
    conn = get_connection()
    try:
        members = [
            r["member_service"]
            for r in conn.execute(
                "SELECT member_service FROM lab_panels WHERE panel_service = ? "
                "ORDER BY member_service",
                (panel_service,),
            )
        ]
        if not members:
            return {"status": "no_data", "panel": panel_service,
                    "message": f"'{panel_service}' is not a known panel."}

        panel_row = conn.execute(
            "SELECT service, price_low, price_high, as_of, mmc_code FROM hospital_prices "
            "WHERE service = ?",
            (panel_service,),
        ).fetchone()
        if panel_row is None:
            return {"status": "no_data", "panel": panel_service,
                    "message": f"MMC publishes no price for the panel '{panel_service}'."}
        panel_row = dict(panel_row)

        priced, missing = [], []
        for m in members:
            row = conn.execute(
                "SELECT service, price_low, price_high, mmc_code FROM hospital_prices "
                "WHERE service = ?",
                (m,),
            ).fetchone()
            (priced if row is not None else missing).append(dict(row) if row else m)

        if missing:
            return {
                "status": "incomplete",
                "panel": panel_service,
                "panel_price_low": panel_row["price_low"],
                "panel_price_high": panel_row["price_high"],
                "members_priced": priced,
                "members_missing": missing,
                "message": "Some member tests have no published price, so the components "
                           "total would be understated. Comparison withheld.",
            }

        comp_low = sum(r["price_low"] for r in priced)
        comp_high = sum(r["price_high"] for r in priced)
        # Compare low-to-low and high-to-high; the saving is itself a range.
        saving_low = comp_low - panel_row["price_low"]
        saving_high = comp_high - panel_row["price_high"]

        if saving_low > 0 and saving_high > 0:
            cheaper = "panel"
        elif saving_low < 0 and saving_high < 0:
            cheaper = "components"
        else:
            cheaper = None  # crosses over -- depends where in the range you land

        return {
            "status": "ok",
            "panel": panel_service,
            "panel_price_low": panel_row["price_low"],
            "panel_price_high": panel_row["price_high"],
            "components_price_low": comp_low,
            "components_price_high": comp_high,
            "members": priced,
            "saving_low": saving_low,
            "saving_high": saving_high,
            "cheaper": cheaper,
            "as_of": panel_row["as_of"],
        }
    finally:
        conn.close()
