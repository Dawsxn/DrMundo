"""API tests for the slip-upload and refine endpoints (Phase 9).

No model is called: the service is driven with the OracleReader so these run offline and
deterministically. What is under test is the HTTP layer and the two-pass flow, not the
reader.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api
from eval.reader_bench import dataset_dir
from vision.reader import OracleReader


@pytest.fixture()
def client(monkeypatch):
    """Force the oracle reader so no API call is made."""
    base = dataset_dir()
    original = api.SERVICE.handle_slip

    def _offline(image_path, session_id="default", **kw):
        # The endpoint writes the upload to a randomly-named temp file (deliberately: the
        # patient's filename could itself carry their name). The oracle keys on sample id,
        # so point it at the known image instead. The HTTP layer is what is under test.
        kw["reader"] = OracleReader(base / "groundtruth")
        kw.setdefault("synthetic", True)
        return original(base / "media" / "0000000_clean.png", session_id=session_id, **kw)

    monkeypatch.setattr(api.SERVICE, "handle_slip", _offline)
    api.SERVICE.reset_session("t")
    return TestClient(api.app)


def _slip_bytes(sample_id: str = "0000000") -> tuple[str, bytes]:
    base = dataset_dir()
    gt = json.loads((base / "groundtruth" / f"{sample_id}.json").read_text(encoding="utf-8"))
    name = Path(gt["image"]).name
    return name, (base / "media" / name).read_bytes()


# ------------------------------------------------------------------ the text path
def test_existing_endpoints_are_untouched(client):
    assert client.get("/health").json()["status"] == "ok"
    paths = {r.path for r in api.app.routes if hasattr(r, "path")}
    assert {"/ask", "/reset", "/ask-slip", "/refine"} <= paths


# ------------------------------------------------------------------ upload validation
def test_non_image_upload_is_rejected(client):
    r = client.post("/ask-slip", files={"file": ("x.txt", b"hello", "text/plain")},
                    data={"session_id": "t"})
    assert r.status_code == 415


def test_empty_upload_is_rejected(client):
    r = client.post("/ask-slip", files={"file": ("x.png", b"", "image/png")},
                    data={"session_id": "t"})
    assert r.status_code in (400, 413)


def test_oversized_upload_is_rejected(client):
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (api.MAX_UPLOAD_BYTES + 1)
    r = client.post("/ask-slip", files={"file": ("big.png", big, "image/png")},
                    data={"session_id": "t"})
    assert r.status_code == 413


# ------------------------------------------------------------------ pass 1
def test_slip_upload_returns_a_priced_report(client):
    name, payload = _slip_bytes()
    r = client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                    data={"session_id": "t"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]["path"] == "budget_report"
    budget = body["answer"]["budget"]
    assert budget["extracted_count"] == 7
    assert len(budget["priced"]) == 7
    assert float(budget["prepare_low"]) > 0


def test_pass_one_asks_nothing_and_says_before_any_hmo(client):
    name, payload = _slip_bytes()
    r = client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                    data={"session_id": "t"})
    caveats = r.json()["answer"]["budget"]["caveats"]
    assert any("before any HMO" in c for c in caveats)


def test_upload_leaves_no_file_behind_in_the_repo(client, tmp_path):
    name, payload = _slip_bytes()
    before = set(Path(".").glob("*.png"))
    client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                data={"session_id": "t"})
    assert set(Path(".").glob("*.png")) == before


# ------------------------------------------------------------------ pass 2
def test_refine_reprices_without_a_second_upload(client):
    name, payload = _slip_bytes()
    first = client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                        data={"session_id": "t"}).json()
    before = float(first["answer"]["budget"]["prepare_low"])

    r = client.post("/refine", json={
        "session_id": "t",
        "hmo_provider": "Maxicare",
        "hmo_plan": "Gold",
        "hmo_remaining_balance": "40000",
    })
    assert r.status_code == 200
    after = float(r.json()["answer"]["budget"]["prepare_low"])
    assert after < before


def test_refine_accepts_a_comma_formatted_balance(client):
    name, payload = _slip_bytes()
    client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                data={"session_id": "t"})
    r = client.post("/refine", json={"session_id": "t", "hmo_provider": "Maxicare",
                                     "hmo_plan": "Gold",
                                     "hmo_remaining_balance": "40,000"})
    assert r.status_code == 200


def test_refine_rejects_a_non_numeric_balance(client):
    name, payload = _slip_bytes()
    client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                data={"session_id": "t"})
    r = client.post("/refine", json={"session_id": "t", "hmo_remaining_balance": "lots"})
    assert r.status_code == 422


def test_no_procedure_planned_is_a_real_answer(client):
    name, payload = _slip_bytes()
    client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                data={"session_id": "t"})
    r = client.post("/refine", json={"session_id": "t", "no_procedure_planned": True})
    caveats = r.json()["answer"]["budget"]["caveats"]
    assert any("No operation is planned" in c for c in caveats)
    assert not any("tell me which one" in c for c in caveats)


def test_refine_without_a_slip_says_so(client):
    api.SERVICE.reset_session("empty")
    r = client.post("/refine", json={"session_id": "empty", "senior_or_pwd": True})
    assert r.status_code == 200
    assert "Upload a request slip" in r.json()["answer"]["answer_text"]


def test_reset_clears_the_slip_too(client):
    name, payload = _slip_bytes()
    client.post("/ask-slip", files={"file": (name, payload, "image/png")},
                data={"session_id": "t"})
    client.post("/reset", json={"session_id": "t"})
    r = client.post("/refine", json={"session_id": "t", "senior_or_pwd": True})
    assert "Upload a request slip" in r.json()["answer"]["answer_text"]
