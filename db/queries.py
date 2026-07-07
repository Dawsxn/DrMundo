"""Parameterized, read-only SQL query functions -- the ONLY place SQL is written.

The LLM never generates SQL. It picks which of these typed functions to call and fills
their arguments; these functions run fixed, parameterized statements and return plain
dicts/lists. Every function returns a `status` so the agent can react instead of the
function raising:
    "ok"                  -> data found
    "no_data"             -> nothing matched (e.g. procedure not priced anywhere)
    "needs_clarification" -> ambiguous hospital name; `candidates` lists the options
"""

import sqlite3

from db.aliases import equivalent_services
from db.connection import get_connection


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
def _compute_oop(case_rate: float, price_low: int, price_high: int) -> dict:
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
                "SELECT hpp.hospital_id, h.hospital, h.city, hpp.price_low, hpp.price_high, hpp.as_of "
                "FROM hospital_procedure_prices hpp JOIN hospitals h ON h.id = hpp.hospital_id "
                "WHERE hpp.rvs_code = ? AND hpp.hospital_id = ?",
                (proc["rvs_code"], target_hospital["id"]),
            ).fetchall()
        else:
            price_rows = conn.execute(
                "SELECT hpp.hospital_id, h.hospital, h.city, hpp.price_low, hpp.price_high, hpp.as_of "
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
            oop = _compute_oop(case_rate, r["price_low"], r["price_high"])
            breakdown.append({
                "hospital_id": r["hospital_id"], "hospital": r["hospital"], "city": r["city"],
                "price_low": r["price_low"], "price_high": r["price_high"],
                "oop_low": oop["oop_low"], "oop_high": oop["oop_high"],
                "fully_covered": oop["fully_covered"],
            })

        price_low = min(r["price_low"] for r in price_rows)
        price_high = max(r["price_high"] for r in price_rows)
        oop = _compute_oop(case_rate, price_low, price_high)
        as_of = price_rows[0]["as_of"]

        return {
            **base,
            "hospital": target_hospital,           # None -> across all hospitals
            "price_low": price_low,
            "price_high": price_high,
            **oop,
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
