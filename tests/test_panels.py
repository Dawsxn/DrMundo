"""Unit tests for the panel comparison advisory (uses the DB, no API)."""

from decimal import Decimal

from pricing.panels import compare_panels_on_slip, panel_advisory_text
from pricing.schemas import PricedItem
from vision.schemas import ExtractedItem

LIPID_FULL = "LIPID PROFILE (HDL LDL CHOL TRIG) SERUM"


def _priced(name: str, low: str = "1", high: str = "2") -> PricedItem:
    return PricedItem(
        item=ExtractedItem(raw_text=name, normalized=name, kind="lab", ocr_confidence=0.9),
        mmc_code="X",
        catalog_name=name,
        price_low=Decimal(low),
        price_high=Decimal(high),
        match_confidence=0.9,
    )


def test_panel_on_slip_is_compared():
    out = compare_panels_on_slip([_priced(LIPID_FULL)])
    assert len(out) == 1
    c = out[0]
    assert c["status"] == "ok"
    assert c["cheaper"] == "panel"
    assert c["saving_low"] == Decimal("70")
    assert c["saving_high"] == Decimal("700")


def test_non_panel_items_produce_no_advisory():
    assert compare_panels_on_slip([_priced("CBC (COMPLETE BLOOD COUNT)")]) == []


def test_advisory_text_names_the_saving():
    c = compare_panels_on_slip([_priced(LIPID_FULL)])[0]
    text = panel_advisory_text(c)
    assert "save" in text
    assert "70" in text and "700" in text


def test_panel_plus_its_own_member_is_flagged_not_silently_deduped():
    # Removing an ordered test from an estimate is a clinical decision, not a pricing one.
    out = compare_panels_on_slip([_priced(LIPID_FULL), _priced("HDL")])
    c = next(x for x in out if x["panel"] == LIPID_FULL)
    assert c["already_has_members"] == ["HDL"]
    assert "already includes" in panel_advisory_text(c)


def test_all_three_panels_are_detected_and_favour_the_panel():
    panels = [
        "LIPID PROFILE (HDL & LDL) SERUM",
        LIPID_FULL,
        "LIPID PROFILE (HDL LDL TRIG) SERUM",
    ]
    out = compare_panels_on_slip([_priced(p) for p in panels])
    assert len(out) == 3
    assert all(c["cheaper"] == "panel" for c in out)


def test_comparison_is_advisory_only():
    # It reports; it does not change any price the waterfall will charge.
    item = _priced(LIPID_FULL, low="4450", high="8700")
    compare_panels_on_slip([item])
    assert item.price_low == Decimal("4450")
    assert item.price_high == Decimal("8700")
