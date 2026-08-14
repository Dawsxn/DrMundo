"""Unit tests for the raw-SQL query layer, run against the real built DB.

Scope v2: a single hospital (Makati Medical Center) and prices sourced from MMC's published
price list, so every expected figure below is a real published number, not a fixture.
"""

import pytest

from db.queries import (
    get_covered_cost,
    get_outpatient_cost,
    list_hospitals,
)


# --- list_hospitals -------------------------------------------------------------------
def test_list_all_hospitals():
    assert len(list_hospitals()) == 1


def test_filter_hospital_by_city():
    assert [h["hospital"] for h in list_hospitals(city="makati")] == ["Makati Medical Center"]


def test_filter_hospital_by_name_substring():
    names = [h["hospital"] for h in list_hospitals(name_query="medical")]
    assert names == ["Makati Medical Center"]


# --- get_covered_cost (Path A) --------------------------------------------------------
def test_covered_aggregates_multiple_packages():
    # 47562 (laparoscopic cholecystectomy) is priced by TWO MMC packages -- the plain one
    # and the "W/ ICG" variant -- so the range must span both.
    r = get_covered_cost("47562")
    assert r["status"] == "ok"
    assert r["case_rate"] == 60450.0
    assert r["price_low"] == 150000 and r["price_high"] == 208500
    assert len(r["hospitals"]) == 2
    assert r["oop_low"] == 150000 - 60450
    assert r["oop_high"] == 208500 - 60450


def test_covered_single_hospital_resolves_by_name():
    r = get_covered_cost("47562", hospital="makati")
    assert r["status"] == "ok"
    assert r["hospital"]["hospital"] == "Makati Medical Center"


def test_covered_partial_coverage_low_end():
    # 50590 (ESWL): the P35,100 case rate sits INSIDE the P22,700-70,900 price range, so
    # PhilHealth covers the low end fully but not the high end.
    r = get_covered_cost("50590")
    assert r["price_low"] == 22700 and r["price_high"] == 70900
    assert r["case_rate"] == 35100.0
    assert r["oop_low"] == 0.0
    assert r["oop_high"] == 70900 - 35100
    assert r["fully_covered"] is False


def test_covered_procedure_without_hospital_price():
    # A real covered procedure (has a case rate) that MMC does not publish a price for.
    # This is the common case now: 4,312 case rates vs ~50 priced procedures.
    r = get_covered_cost("50365")
    assert r["status"] == "ok"
    assert r["case_rate"] > 0
    assert r["price_low"] is None and r["price_high"] is None
    assert "no hospital price" in r["message"].lower()


def test_covered_unknown_code_is_no_data():
    assert get_covered_cost("00000")["status"] == "no_data"


@pytest.mark.skip(reason="Unreachable with a single hospital: _resolve_hospital's 'multiple' "
                         "branch needs two hospitals matching one substring. The code path is "
                         "unchanged and still correct -- re-enable if a hospital is added.")
def test_covered_ambiguous_hospital_needs_clarification():
    r = get_covered_cost("47562", hospital="medical")
    assert r["status"] == "needs_clarification"


# --- get_outpatient_cost (Path B) -----------------------------------------------------
def test_outpatient_aggregates_equivalent_variants():
    # SERVICE_EQUIVALENTS groups MMC's own near-identical listings so a price question spans
    # the whole family rather than one arbitrary variant.
    r = get_outpatient_cost("CHEST PA")
    assert r["status"] == "ok"
    assert r["philhealth_covered"] is False
    assert "case_rate" not in r          # Path B never has a case rate / OOP
    assert "oop_low" not in r
    assert {h["service"] for h in r["hospitals"]} == {"CHEST PA", "CHEST PA & LATERAL"}


def test_outpatient_variant_name_resolves_to_group():
    # Asking by the sibling name must reach the same group, not just its own row.
    r = get_outpatient_cost("CHEST PA & LATERAL")
    assert r["status"] == "ok"
    assert {h["service"] for h in r["hospitals"]} == {"CHEST PA", "CHEST PA & LATERAL"}


def test_outpatient_specific_hospital():
    r = get_outpatient_cost("CBC (COMPLETE BLOOD COUNT)", hospital="makati")
    assert r["status"] == "ok"
    assert len(r["hospitals"]) == 1
    assert r["price_low"] == 630 and r["price_high"] == 1200


def test_outpatient_unknown_service_is_no_data():
    assert get_outpatient_cost("dragon scale polishing")["status"] == "no_data"
