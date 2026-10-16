import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FX = Path(__file__).parent / "fixtures"
# tests -> agent -> backend -> prototype, so docs/contract is three levels up.
CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "contract"


@pytest.fixture
def client(monkeypatch):
    from agent import main
    monkeypatch.setattr(main, "run_investigation", lambda inv_id: None)
    return TestClient(main.app)


def test_health_reports_the_model_from_env(client, monkeypatch):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert "model" in body


def test_complaints_carry_the_inbox_fields(client):
    rows = client.get("/api/complaints").json()
    golden = next(c for c in rows if c["complaint_id"] == "C-2026-031")
    assert golden["customer"] == "Hoshino Denso (fictional)"
    assert golden["product"] == "ECU-PCB-7"
    assert golden["lot_id"] == "L2611"
    assert "due_in_working_days" in golden


def test_creating_an_investigation_returns_id_and_running(client):
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "solder bridging"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"].startswith("inv_")
    assert body["status"] == "running"


def test_creating_without_an_image_is_rejected(client):
    resp = client.post("/api/investigations",
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "x"})
    assert resp.status_code == 422


def test_unknown_investigation_is_404(client):
    assert client.get("/api/investigations/inv_nope").status_code == 404


def test_mock_investigation_matches_the_response_model():
    """The file Susan builds against must deserialise as a real Investigation."""
    from agent.models import Investigation
    inv = Investigation.model_validate(json.loads((CONTRACT / "mock_investigation.json").read_text()))
    assert inv.status in ("running", "draft_ready", "approved", "insufficient_evidence")
    assert inv.eight_d is not None
    assert {a.kind for a in inv.proposed_actions} == {"capa", "hold", "work_order", "customer_reply"}


def test_mock_events_match_the_event_model():
    from agent.models import Event
    events = [Event.model_validate(e)
              for e in json.loads((CONTRACT / "mock_events.json").read_text())]
    assert [e.seq for e in events] == list(range(len(events)))
    assert events[-1].type == "done"
    assert any(e.type == "hypothesis_result" and e.data["verdict"] == "supported" for e in events)
    assert sum(1 for e in events
               if e.type == "hypothesis_result" and e.data["verdict"] == "rejected") == 2


def test_sse_stream_is_an_event_stream(client, monkeypatch):
    from agent import main
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "x"})
    inv_id = resp.json()["id"]
    with client.stream("GET", f"/api/investigations/{inv_id}/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        first = next(stream.iter_lines())
        assert first.startswith("data: ")


def test_memory_endpoint_returns_a_list(client):
    assert isinstance(client.get("/api/memory").json(), list)
