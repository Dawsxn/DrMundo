"""Unit tests for the curated alias + equivalence maps (no API, no DB)."""

from db.aliases import (
    canonical_service,
    equivalent_services,
    match_aliases,
)


def test_taglish_delivery_defaults_to_vaginal():
    # "manganak" / "normal delivery" must resolve to vaginal delivery (59409), not C-section.
    assert ("covered", "59409") in match_aliases("magkano ang normal delivery")
    assert ("covered", "59409") in match_aliases("gusto ko manganak")


def test_cs_resolves_to_cesarean():
    assert ("covered", "59514") in match_aliases("how much is a cs")
    assert ("covered", "59514") in match_aliases("cesarean section cost")


def test_common_procedure_aliases():
    assert ("covered", "44950") in match_aliases("appendectomy")
    assert ("covered", "47600") in match_aliases("gallbladder removal")
    assert ("covered", "27447") in match_aliases("total knee replacement")


def test_outpatient_abbreviations():
    assert ("outpatient", "Chest X-ray") in match_aliases("chest xray please")
    assert ("outpatient", "CT Scan (plain)") in match_aliases("how much is a ct scan")
    assert ("outpatient", "Ultrasound (abdomen)") in match_aliases("ultrasound ng tiyan")


def test_no_false_positive_on_unrelated_text():
    assert match_aliases("what is the weather today") == []


def test_word_boundary_prevents_substring_false_match():
    # "cs" alias should not fire inside an unrelated word like "physics".
    assert ("covered", "59514") not in match_aliases("i study physics")


def test_service_equivalence_grouping():
    # Cardinal Santos' variant maps back to the shared canonical group.
    assert canonical_service("CT Scan (plain, single region)") == "CT Scan (plain)"
    members = equivalent_services("CT Scan (plain)")
    assert "CT Scan (plain)" in members
    assert "CT Scan (plain, single region)" in members
    # plain and contrast must stay distinct.
    assert "CT Scan (contrast)" not in members


def test_ungrouped_service_maps_to_itself():
    assert canonical_service("CBC") == "CBC"
    assert equivalent_services("CBC") == ["CBC"]
