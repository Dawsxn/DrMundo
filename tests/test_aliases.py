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
    # 47562 is the laparoscopic cholecystectomy MMC actually prices (47600 is the open
    # operation, which MMC publishes no package for).
    assert ("covered", "47562") in match_aliases("gallbladder removal")
    assert ("covered", "27447") in match_aliases("total knee replacement")
    assert ("covered", "54152") in match_aliases("magkano ang tuli")


def test_outpatient_abbreviations():
    # Canonical strings are MMC's own verbose catalogue names -- the whole point of the
    # alias layer is that nobody types them.
    assert ("outpatient", "CHEST PA") in match_aliases("chest xray please")
    assert ("outpatient", "CBC (COMPLETE BLOOD COUNT)") in match_aliases("magkano ang cbc")
    assert ("outpatient", "WHOLE ABDOMEN") in match_aliases("ultrasound ng tiyan")


def test_no_false_positive_on_unrelated_text():
    assert match_aliases("what is the weather today") == []


def test_word_boundary_prevents_substring_false_match():
    # "cs" alias should not fire inside an unrelated word like "physics".
    assert ("covered", "59514") not in match_aliases("i study physics")


def test_service_equivalence_grouping():
    # MMC's sibling listing maps back to the shared canonical group.
    assert canonical_service("CHEST PA & LATERAL") == "CHEST PA"
    members = equivalent_services("CHEST PA")
    assert "CHEST PA" in members
    assert "CHEST PA & LATERAL" in members
    # A panel and its individual member test must stay distinct -- grouping them would
    # destroy the "is the panel cheaper?" comparison.
    lipid = equivalent_services("LIPID PROFILE (HDL LDL CHOL TRIG) SERUM")
    assert "HDL" not in lipid


def test_ungrouped_service_maps_to_itself():
    assert canonical_service("HbA1C") == "HbA1C"
    assert equivalent_services("HbA1C") == ["HbA1C"]
