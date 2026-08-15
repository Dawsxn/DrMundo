"""GET /coverage: what the session says the patient's cover is.

The panel is persistent and cannot be built from the last reply alone. A plan may have
arrived from a document, from answering the HMO question, or ten turns ago, and only the
session knows which.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.main import SERVICE, app
from pricing.schemas import HMOPlan


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_sessions():
    yield
    SERVICE._sessions.pop("cov-test", None)


def test_an_unknown_session_reports_no_cover(client):
    body = client.get("/coverage", params={"session_id": "nobody-at-all"}).json()

    assert body["plan"] is None
    assert body["has_schedule"] is False
    assert body["sublimit_count"] == 0


def test_reading_coverage_does_not_create_a_session(client):
    """A GET that manufactures state would leak a session per page render, and the panel
    renders on every rerun."""
    client.get("/coverage", params={"session_id": "ghost-session"})

    assert "ghost-session" not in SERVICE._sessions


def test_a_plan_without_a_schedule_is_reported_as_such(client):
    SERVICE._memory("cov-test").hmo = HMOPlan(
        provider="Maxicare", plan_name="Gold", mbl_annual=Decimal(150_000))

    body = client.get("/coverage", params={"session_id": "cov-test"}).json()

    assert body["plan"]["plan_name"] == "Gold"
    assert body["has_schedule"] is False
    assert body["sublimit_count"] == 0


def test_a_parsed_schedule_is_reported_with_its_limits(client):
    SERVICE._memory("cov-test").hmo = HMOPlan(
        provider="Maxicare", plan_name="Gold", mbl_annual=Decimal(150_000),
        outpatient_diagnostics_limit=Decimal(20_000),
        procedure_sublimits={"Laparoscopic cholecystectomy": Decimal(60_000),
                             "MRI": Decimal(18_000)},
        schedule_source="uploaded_document",
    )

    body = client.get("/coverage", params={"session_id": "cov-test"}).json()

    assert body["has_schedule"] is True
    assert body["sublimit_count"] == 2
    assert float(body["plan"]["outpatient_diagnostics_limit"]) == 20_000
