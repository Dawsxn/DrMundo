"""The persistent coverage panel: what it says about the patient's plan.

The panel is the only place that states, continuously, whether we are working from the
patient's real limits or from a ceiling. Getting that line wrong is worse than not showing
it: "real limits in use" over an assumed figure is a claim we cannot support.

Only the pure summary is tested here. The rendering around it is three Streamlit calls.
"""

import pytest

from ui.app import EMPTY_COVERAGE, coverage_summary


def _payload(**plan) -> dict:
    base = {"plan_name": "Gold", "mbl_annual": 150000, "room_entitlement": "Regular Private"}
    return {"plan": {**base, **plan}, "has_schedule": False, "sublimit_count": 0}


def test_no_plan_invites_the_upload():
    for data in ({}, {"plan": None}):
        s = coverage_summary(data)
        assert s["headline"] == ""
        assert s["note"] == EMPTY_COVERAGE
        assert "Add" in s["upload_label"]


def test_a_plan_is_summarised_in_one_line():
    s = coverage_summary(_payload())

    assert "**Gold**" in s["headline"]
    assert "₱150,000 per illness/year" in s["headline"]
    assert "Regular Private" in s["headline"]
    assert "Replace" in s["upload_label"]


def test_without_a_schedule_the_panel_says_the_figures_are_a_ceiling():
    s = coverage_summary(_payload())

    assert "ceiling" in s["note"]
    assert "real limits in use" not in s["note"]


def test_with_a_schedule_the_panel_says_the_limits_are_real():
    data = _payload(outpatient_diagnostics_limit=20000)
    data.update(has_schedule=True, sublimit_count=8)

    s = coverage_summary(data)

    assert "8 per-procedure limits" in s["note"]
    assert "outpatient ₱20,000" in s["note"]
    assert "real limits in use" in s["note"]
    assert "ceiling" not in s["note"]


def test_one_sublimit_is_singular():
    data = _payload()
    data.update(has_schedule=True, sublimit_count=1)

    assert "1 per-procedure limit &middot;" in coverage_summary(data)["note"]


def test_a_stated_remaining_balance_is_shown():
    """The figure most likely to bind, and the only one the patient typed themselves."""
    s = coverage_summary(_payload(remaining_balance=40000))

    assert "₱40,000 left" in s["note"]


def test_a_plan_known_only_by_provider_still_renders():
    s = coverage_summary({"plan": {"provider": "Maxicare"}})

    assert "**Maxicare**" in s["headline"]


@pytest.mark.parametrize("amount", ["150000", 150000, 150000.0])
def test_money_survives_json_decimal_encoding(amount):
    """Decimal fields arrive over JSON as strings. Formatting them as floats crashed the
    UI once already with "Unknown format code 'f' for object of type 'str'"."""
    s = coverage_summary(_payload(mbl_annual=amount))

    assert "₱150,000 per illness/year" in s["headline"]
