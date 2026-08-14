"""Unit tests for the Scope v2 query layer (DB, no API).

Golden values come from HANDOFF_SCOPE_V2_DATA.md and are verified against the rebuilt
database. If one of these fails after a data rebuild, the DATA changed -- check that
before changing the test.
"""

from db.queries import (
    CRITICAL_CARE_TYPES,
    ROOM_TYPES,
    get_covered_cost,
    get_facility_rates,
    get_panel_comparison,
    get_professional_fees,
)

LIPID_FULL = "LIPID PROFILE (HDL LDL CHOL TRIG) SERUM"


# ------------------------------------------------------------------ price_basis surfacing
def test_covered_cost_surfaces_price_basis_and_confidence():
    # 47562 = laparoscopic cholecystectomy, the handoff's worked example.
    res = get_covered_cost("47562")
    assert res["status"] == "ok"
    assert res["case_rate"] == 60450
    assert res["price_basis"] == "package"
    assert res["confidence"] in {"high", "medium", "low"}


def test_component_row_never_claims_full_coverage():
    # RVS 57452 colposcopy: MMC charges P4,100 against a P15,639 case rate. Before this
    # guard the app reported "may be fully covered" on a partial price and understated
    # a real bill (handoff §5.4).
    res = get_covered_cost("57452")
    assert res["status"] == "ok"
    assert res["price_basis"] == "component"
    assert res["fully_covered"] is False
    # Out-of-pocket is genuinely uncomputable: we do not know the rest of the episode.
    assert res["oop_low"] is None
    assert res["oop_high"] is None
    assert "only part" in res["coverage_note"]


def test_all_four_component_rows_are_flagged():
    for rvs in ("57452", "57460", "58300", "58260"):
        res = get_covered_cost(rvs)
        assert res["price_basis"] == "component", rvs
        assert res["fully_covered"] is False, rvs


def test_package_row_still_computes_out_of_pocket():
    res = get_covered_cost("47562")
    assert res["oop_low"] is not None and res["oop_high"] is not None


# ------------------------------------------------------------------ facility rates
def test_facility_rates_defaults_to_rooms_only():
    res = get_facility_rates()
    names = {r["room_type"] for r in res["rates"]}
    assert "WARD" in names
    assert "PRESIDENTIAL SUITE" in names
    # The whole point of the allow-list: these are not places to sleep.
    assert "CARDIOVERSION" not in names
    assert "RHYTHM STRIPS 6 SECONDS" not in names
    assert "AIR MATTRESS" not in names


def test_facility_rates_ward_and_suite_match_handoff():
    res = get_facility_rates()
    by_type = {r["room_type"]: r for r in res["rates"]}
    assert by_type["WARD"]["rate_low"] == 1810
    assert by_type["PRESIDENTIAL SUITE"]["rate_low"] == 37200
    assert res["unit"] == "per day"


def test_facility_rates_are_marked_never_in_total():
    # Structural reminder: length of stay is unknowable from a slip (handoff §8).
    assert get_facility_rates()["never_in_total"] is True


def test_critical_care_is_separated_from_elective_rooms():
    rooms = {r["room_type"] for r in get_facility_rates(kind="room")["rates"]}
    crit = {r["room_type"] for r in get_facility_rates(kind="critical_care")["rates"]}
    assert "ICU SURGICAL/MEDICAL/NEURO" in crit
    assert not (rooms & crit)


def test_every_facility_row_is_classified():
    allr = get_facility_rates(kind=None)["rates"]
    assert len(allr) == 34
    assert {r["kind"] for r in allr} <= {"room", "critical_care", "ancillary"}
    assert not (ROOM_TYPES & CRITICAL_CARE_TYPES)


# ------------------------------------------------------------------ professional fees
def test_professional_fees_found_for_appendectomy():
    # The handoff's honest-gap case: MMC publishes fees but no OR package.
    res = get_professional_fees("APPENDECTOMY")
    assert res["status"] == "ok"
    assert res["fees"]
    assert res["excluded_from_total"] is True


def test_professional_fees_missing_is_reported_not_raised():
    res = get_professional_fees("ZZZ NOT A REAL SERVICE")
    assert res["status"] == "no_data"
    assert res["fees"] == []


def test_professional_fees_empty_query_is_no_data():
    assert get_professional_fees("")["status"] == "no_data"


# ------------------------------------------------------------------ panels
def test_lipid_panel_beats_its_components():
    res = get_panel_comparison(LIPID_FULL)
    assert res["status"] == "ok"
    assert res["cheaper"] == "panel"
    # Handoff §10.2: panel 4,450-8,700 vs components 4,520-9,400 -> saves 70 to 700.
    assert res["panel_price_low"] == 4450
    assert res["panel_price_high"] == 8700
    assert res["components_price_low"] == 4520
    assert res["components_price_high"] == 9400
    assert res["saving_low"] == 70
    assert res["saving_high"] == 700


def test_all_three_panels_beat_their_components():
    # Handoff: savings run P60-P1,400 depending on panel and price end.
    panels = [
        "LIPID PROFILE (HDL & LDL) SERUM",
        "LIPID PROFILE (HDL LDL CHOL TRIG) SERUM",
        "LIPID PROFILE (HDL LDL TRIG) SERUM",
    ]
    savings = []
    for p in panels:
        res = get_panel_comparison(p)
        assert res["status"] == "ok", p
        assert res["cheaper"] == "panel", p
        savings += [res["saving_low"], res["saving_high"]]
    assert min(savings) == 60
    assert max(savings) == 1400


def test_unknown_panel_is_no_data():
    assert get_panel_comparison("NOT A PANEL")["status"] == "no_data"


def test_panel_saving_is_a_range_not_a_point():
    res = get_panel_comparison(LIPID_FULL)
    assert res["saving_low"] != res["saving_high"]
