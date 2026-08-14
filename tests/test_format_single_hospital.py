"""Rendering with a single-hospital dataset (Scope v2).

The midterm covered five hospitals, so a per-hospital breakdown made sense. Scope v2
covers one, and several rows for one procedure are several PACKAGES, not several
hospitals. Rendering them as a hospital list printed "Makati Medical Center" twice and
claimed the answer spanned "2 hospitals".
"""

from agent.format import format_answer
from agent.schemas import Answer, HospitalBreakdown
from db.queries import get_covered_cost, get_outpatient_cost


def _answer(res: dict, path: str) -> Answer:
    return Answer(
        status="answered", path=path, query="q", answer_text="",
        procedure_or_service=res.get("procedure") or res.get("service"),
        case_rate=res.get("case_rate"), price_low=res.get("price_low"),
        price_high=res.get("price_high"), oop_low=res.get("oop_low"),
        oop_high=res.get("oop_high"), fully_covered=res.get("fully_covered"),
        as_of=res.get("as_of"),
        hospitals=[HospitalBreakdown(**h) for h in (res.get("hospitals") or [])],
    )


def test_one_hospital_is_named_not_counted():
    text = format_answer(_answer(get_covered_cost("47562"), "covered"))
    assert "at Makati Medical Center" in text
    assert "hospitals" not in text.split("Estimates only")[0]


def test_multiple_rows_render_as_packages_not_repeated_hospitals():
    """RVS 47562 has two MMC packages: plain, and with ICG at P24,500 more."""
    text = format_answer(_answer(get_covered_cost("47562"), "covered"))
    assert "Packages:" in text
    assert "Per hospital" not in text
    assert "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE" in text
    assert "W/ ICG" in text
    # The hospital name must appear once, in the scope line, not once per row.
    assert text.count("Makati Medical Center") == 1


def test_single_row_suppresses_a_pointless_breakdown():
    # One row only repeats the headline range, so printing it twice is noise.
    text = format_answer(_answer(get_outpatient_cost("CBC (COMPLETE BLOOD COUNT)"),
                                 "outpatient"))
    assert "Packages:" not in text
    assert "Per hospital" not in text
    assert "₱630" in text


def test_package_names_come_from_the_crosswalk():
    rows = get_covered_cost("47562")["hospitals"]
    assert len(rows) == 2
    assert all(r["package"] for r in rows)
    assert len({r["package"] for r in rows}) == 2       # genuinely different names
