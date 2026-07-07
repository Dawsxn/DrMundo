"""Unit tests for the raw-SQL query layer, run against the real built DB."""

from db.queries import (
    get_covered_cost,
    get_outpatient_cost,
    list_hospitals,
)


# --- list_hospitals -------------------------------------------------------------------
def test_list_all_hospitals():
    assert len(list_hospitals()) == 5


def test_filter_hospital_by_city():
    cebu = list_hospitals(city="cebu")
    assert [h["hospital"] for h in cebu] == ["Chong Hua Hospital"]


def test_filter_hospital_by_name_substring():
    names = [h["hospital"] for h in list_hospitals(name_query="medical")]
    assert "Makati Medical Center" in names
    assert "The Medical City - Ortigas" in names
    assert "Chong Hua Hospital" not in names  # no "medical" in its name
    assert len(names) == 4


# --- get_covered_cost (Path A) --------------------------------------------------------
def test_covered_across_hospitals():
    r = get_covered_cost("44950")  # appendectomy, priced at all 5 hospitals
    assert r["status"] == "ok"
    assert r["procedure"] == "APPENDECTOMY;"
    assert r["case_rate"] == 46800.0
    assert r["price_low"] == 75000 and r["price_high"] == 220000
    assert len(r["hospitals"]) == 5
    # OOP = price - case_rate
    assert r["oop_low"] == 75000 - 46800
    assert r["oop_high"] == 220000 - 46800


def test_covered_single_hospital_resolves_by_name():
    r = get_covered_cost("44950", hospital="chong hua")
    assert r["status"] == "ok"
    assert r["hospital"]["hospital"] == "Chong Hua Hospital"
    assert len(r["hospitals"]) == 1
    assert r["price_low"] == 75000 and r["price_high"] == 140000


def test_covered_partial_coverage_low_end():
    # 38220: case_rate 21,216 sits between price_low 18,000 and price_high 35,000.
    r = get_covered_cost("38220")
    assert r["oop_low"] == 0.0                     # fully covered at the low end
    assert r["oop_high"] == 35000 - 21216
    assert r["fully_covered"] is False


def test_covered_procedure_without_hospital_price():
    # Real covered procedure (has a case rate) but no hospital price on file.
    r = get_covered_cost("50365")
    assert r["status"] == "ok"
    assert r["case_rate"] > 0
    assert r["price_low"] is None and r["price_high"] is None
    assert "no hospital price" in r["message"].lower()


def test_covered_unknown_code_is_no_data():
    assert get_covered_cost("00000")["status"] == "no_data"


def test_covered_ambiguous_hospital_needs_clarification():
    r = get_covered_cost("44950", hospital="medical")
    assert r["status"] == "needs_clarification"
    assert len(r["candidates"]) == 4


# --- get_outpatient_cost (Path B) -----------------------------------------------------
def test_outpatient_aggregates_equivalent_variants_across_hospitals():
    r = get_outpatient_cost("CT Scan (plain)")
    assert r["status"] == "ok"
    assert r["philhealth_covered"] is False
    assert "case_rate" not in r          # Path B never has a case rate / OOP
    assert "oop_low" not in r
    hospitals = {h["hospital_id"] for h in r["hospitals"]}
    assert hospitals == {1, 2, 3, 4, 5}  # includes Cardinal Santos' single-region variant


def test_outpatient_variant_name_resolves_and_is_covered_by_group():
    r = get_outpatient_cost("CT Scan (plain, single region)")
    assert r["status"] == "ok"
    assert {h["hospital_id"] for h in r["hospitals"]} == {1, 2, 3, 4, 5}


def test_outpatient_specific_hospital():
    r = get_outpatient_cost("Chest X-ray", hospital="cardinal")
    assert r["status"] == "ok"
    assert len(r["hospitals"]) == 1
    assert r["hospitals"][0]["service"] == "Chest X-ray (PA)"  # hospital 5's naming


def test_outpatient_unknown_service_is_no_data():
    assert get_outpatient_cost("dragon scale polishing")["status"] == "no_data"
