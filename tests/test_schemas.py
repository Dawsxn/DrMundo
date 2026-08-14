"""Unit tests for the Scope v2 data contracts (no API, no DB).

These cover the two rules that are enforced at the type boundary rather than by
convention, plus the money representation that the renderer and the grounding guard
must agree on.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from pricing.schemas import (
    BudgetEstimate,
    HMOPlan,
    PricedItem,
    to_display_pesos,
)
from vision.schemas import ExtractedItem, RequestSlip


def _item(raw: str = "CBC", conf: float = 0.9) -> ExtractedItem:
    return ExtractedItem(raw_text=raw, normalized=raw, kind="lab", ocr_confidence=conf)


def _priced(**overrides) -> PricedItem:
    kwargs = dict(
        item=_item(),
        mmc_code="12345",
        catalog_name="CBC (COMPLETE BLOOD COUNT)",
        price_low=Decimal("630"),
        price_high=Decimal("1200"),
        match_confidence=0.9,
    )
    kwargs.update(overrides)
    return PricedItem(**kwargs)


# ------------------------------------------------------------------ redaction gate
def test_unredacted_slip_cannot_be_constructed():
    # An unredacted patient document must fail at the type boundary, not at review.
    with pytest.raises(ValidationError):
        RequestSlip(items=[_item()], image_sha256="abc", redacted=False)


def test_redacted_slip_constructs():
    slip = RequestSlip(items=[_item()], image_sha256="abc", redacted=True)
    assert slip.redacted is True
    assert len(slip.items) == 1


def test_raw_text_and_normalized_stay_separate():
    # The first scores OCR, the second scores matching. Collapsing them makes it
    # impossible to tell which stage failed.
    item = ExtractedItem(
        raw_text="CBC c PC", normalized="CBC (COMPLETE BLOOD COUNT)", kind="lab", ocr_confidence=0.7
    )
    assert item.raw_text != item.normalized


# ------------------------------------------------------------------ count invariant
def test_invariant_passes_when_every_item_is_triaged():
    est = BudgetEstimate(
        priced=[_priced()],
        unpriced=[_item("FECALYSIS")],
        needs_confirmation=[_item("CREA")],
        extracted_count=3,
    )
    assert len(est.priced) + len(est.unpriced) + len(est.needs_confirmation) == 3


def test_invariant_raises_when_an_item_is_dropped():
    # Three items extracted, only two accounted for -- the silent-underquote bug.
    with pytest.raises(ValidationError) as exc:
        BudgetEstimate(
            priced=[_priced()],
            unpriced=[_item("FECALYSIS")],
            needs_confirmation=[],
            extracted_count=3,
        )
    assert "item accounting broken" in str(exc.value)


def test_invariant_raises_when_an_item_is_double_counted():
    item = _item("SODIUM")
    with pytest.raises(ValidationError):
        BudgetEstimate(
            priced=[],
            unpriced=[item],
            needs_confirmation=[item],  # same item in two buckets
            extracted_count=1,
        )


def test_empty_slip_is_valid():
    # Zero items extracted is a real outcome (unreadable slip), not an error here.
    est = BudgetEstimate(extracted_count=0)
    assert est.prepare_low == Decimal(0)


# ------------------------------------------------------------------ money
def test_decimal_survives_construction_exactly():
    est = BudgetEstimate(extracted_count=0, prepare_low=Decimal("1810.50"))
    assert est.prepare_low == Decimal("1810.50")
    assert isinstance(est.prepare_low, Decimal)


def test_display_rounding_is_half_up_not_bankers():
    # Python's round() would give 12400 here (banker's rounding); a patient expects 12401.
    assert to_display_pesos(Decimal("12400.5")) == 12401
    assert to_display_pesos(Decimal("12401.5")) == 12402
    assert to_display_pesos(Decimal("12400.4")) == 12400


def test_display_rounding_is_stable_on_whole_pesos():
    assert to_display_pesos(Decimal("60450")) == 60450


def test_senior_pwd_multiplier_lands_where_expected():
    # 0.714286 = VAT exemption (1/1.12) x 20% discount. Omitting the VAT exemption and
    # applying only the 20% is the bug that actually costs money.
    gross = Decimal("10000")
    assert to_display_pesos(gross * Decimal("0.714286")) == 7143


# ------------------------------------------------------------------ coverage guards
def test_component_price_basis_blocks_full_coverage_claim():
    # RVS 57452 colposcopy: MMC charges P4,100, case rate is P15,639 -- a partial price.
    est = BudgetEstimate(
        priced=[
            _priced(
                price_basis="component",
                rvs_code="57452",
                case_rate=Decimal("15639"),
                price_high=Decimal("4100"),
            )
        ],
        extracted_count=1,
    )
    assert est.has_component_priced_item is True


def test_package_price_basis_does_not_block():
    est = BudgetEstimate(
        priced=[_priced(price_basis="package", rvs_code="47562", case_rate=Decimal("60450"))],
        extracted_count=1,
    )
    assert est.has_component_priced_item is False


# ------------------------------------------------------------------ HMO
def test_published_tier_figures_are_flagged_for_verification():
    plan = HMOPlan(provider="Maxicare", plan_name="Gold", mbl_annual=Decimal("100000"),
                   mbl_source="published_tier")
    assert plan.needs_verification_note is True


def test_patient_stated_figures_are_not_flagged():
    plan = HMOPlan(mbl_annual=Decimal("80000"), mbl_source="patient_stated")
    assert plan.needs_verification_note is False


def test_hmo_plan_defaults_to_no_figures():
    # "No plan given" must be representable without implying zero coverage.
    plan = HMOPlan()
    assert plan.mbl_annual is None
    assert plan.remaining_balance is None
