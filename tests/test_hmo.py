"""Tests for HMO plan resolution (Phase 6).

Figures come from data/hmo_published_tiers.csv, read from Maxicare's own plan page on
2026-08-15. If one of these fails after a table update, check the page before changing the
expectation -- and see data/HMO_TIERS_PROVENANCE.md, which records that a web search got
all four tiers wrong.
"""

from decimal import Decimal

import pytest

from pricing.hmo import list_plans, mmc_room_type, resolve_hmo_plan
from pricing.waterfall import compute_budget
from pricing.schemas import PricedItem
from vision.schemas import ExtractedItem


def _priced(low: str, high: str) -> PricedItem:
    item = ExtractedItem(raw_text="CBC", normalized="CBC", kind="lab")
    return PricedItem(item=item, mmc_code="X", catalog_name="CBC",
                      price_low=Decimal(low), price_high=Decimal(high), match_confidence=0.9)


# ------------------------------------------------------------------ the table
def test_four_maxicare_tiers_are_published():
    plans = list_plans("Maxicare")
    assert len(plans) == 4
    assert {p["plan_name"] for p in plans} == {"Platinum Plus", "Platinum", "Gold", "Silver"}


def test_published_mbls_match_maxicares_own_page():
    got = {p["plan_name"]: p["mbl_annual"] for p in list_plans("Maxicare")}
    assert got == {
        "Platinum Plus": "250000",
        "Platinum": "200000",
        "Gold": "150000",
        "Silver": "100000",
    }


def test_every_row_carries_a_source_url():
    for p in list_plans():
        assert p["source"].startswith("https://"), p


# ------------------------------------------------------------------ resolution
def test_named_plan_prefills_mbl_and_is_flagged_as_published():
    plan = resolve_hmo_plan("Maxicare", "Gold")
    assert plan.mbl_annual == Decimal("150000")
    assert plan.mbl_source == "published_tier"
    assert plan.needs_verification_note is True


def test_matching_is_forgiving_about_case_and_spacing():
    assert resolve_hmo_plan("maxicare", "platinum plus").mbl_annual == Decimal("250000")
    assert resolve_hmo_plan("MAXICARE", "Platinum-Plus").mbl_annual == Decimal("250000")


def test_longer_name_does_not_collapse_to_the_shorter_tier():
    # "Platinum Plus" must not resolve to "Platinum" -- a P50,000 difference.
    assert resolve_hmo_plan("Maxicare", "Platinum Plus").plan_name == "Platinum Plus"
    assert resolve_hmo_plan("Maxicare", "Platinum").plan_name == "Platinum"


def test_unknown_plan_is_the_expected_case_not_an_error():
    # Most PH coverage is employer-provided and negotiated; a corporate plan matches
    # nothing here. The agent asks for the MBL instead.
    plan = resolve_hmo_plan("Maxicare", "Corporate Executive Plan B")
    assert plan.mbl_annual is None
    assert plan.mbl_source is None
    assert plan.plan_name == "Corporate Executive Plan B"


def test_no_plan_name_resolves_to_nothing():
    plan = resolve_hmo_plan("Maxicare", None)
    assert plan.mbl_annual is None


def test_patient_stated_mbl_overrides_the_published_tier():
    # Their own certificate beats a published tier for a plan they may not hold.
    plan = resolve_hmo_plan("Maxicare", "Gold", mbl_annual=Decimal("80000"))
    assert plan.mbl_annual == Decimal("80000")
    assert plan.mbl_source == "patient_stated"
    assert plan.needs_verification_note is False


def test_remaining_balance_is_only_ever_patient_stated():
    plan = resolve_hmo_plan("Maxicare", "Gold")
    assert plan.remaining_balance is None
    plan2 = resolve_hmo_plan("Maxicare", "Gold", remaining_balance=Decimal("40000"))
    assert plan2.remaining_balance == Decimal("40000")


# ------------------------------------------------------------------ room mapping
def test_room_type_maps_only_where_the_vocabularies_agree():
    assert mmc_room_type(resolve_hmo_plan("Maxicare", "Platinum Plus")) == "LARGE PRIVATE"
    assert mmc_room_type(resolve_hmo_plan("Maxicare", "Silver")) == "SEMI PRIVATE"


def test_regular_private_is_left_unmapped_rather_than_guessed():
    # MMC publishes SMALL / LARGE / PREMIUM LARGE PRIVATE. There is no "Regular Private",
    # and guessing would silently change what a patient is told they are entitled to.
    assert mmc_room_type(resolve_hmo_plan("Maxicare", "Gold")) is None
    assert resolve_hmo_plan("Maxicare", "Gold").room_entitlement == "Regular Private"


# ------------------------------------------------------------------ end to end
def test_resolved_plan_drives_the_waterfall():
    plan = resolve_hmo_plan("Maxicare", "Gold", remaining_balance=Decimal("40000"))
    est = compute_budget(priced=[_priced("100000", "100000")], hmo=plan)
    assert est.hmo_low == Decimal("40000")
    assert est.prepare_low == Decimal("60000")


def test_published_tier_without_a_balance_is_capped_by_the_mbl():
    # No balance stated: the MBL is the only ceiling, and the figure is an upper bound on
    # HMO help rather than a computed balance.
    plan = resolve_hmo_plan("Maxicare", "Silver")
    est = compute_budget(priced=[_priced("500000", "500000")], hmo=plan)
    assert est.hmo_low == Decimal("100000")
    assert any("your own certificate" in c for c in est.caveats)


def test_unresolved_plan_leaves_the_estimate_before_any_hmo():
    plan = resolve_hmo_plan("Maxicare", "Some Corporate Plan")
    est = compute_budget(priced=[_priced("5000", "5000")], hmo=plan)
    assert est.hmo_low == Decimal("0")
    assert any("before any HMO" in c for c in est.caveats)
