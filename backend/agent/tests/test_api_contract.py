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
    from agent.events import bus

    async def fake_run_investigation(inv_id):
        """Mirrors what orchestrator.run_investigation actually guarantees on
        success — publish done, close the bus — rather than a non-awaitable stub
        that crashes and relies on main._run's backstop to terminate the stream.
        The SSE test below must pass because termination works, not because the
        stub raises a TypeError."""
        await bus.publish(inv_id, "system", "done", "Investigation complete")
        bus.close(inv_id)

    monkeypatch.setattr(main, "run_investigation", fake_run_investigation)
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


def test_the_uploaded_photo_is_saved_and_fetchable(client):
    """Investigation.photo_url used to stay '' forever — nothing ever wrote it, so the
    UI's defect photo (and its bounding box overlay) had nothing to point an <img> at
    in live mode. orchestrator.start() now saves the upload through the same files
    backend as the stats charts; this is the end-to-end proof that the URL it returns
    is one `GET /api/files/...` can actually serve the bytes back from."""
    image_bytes = (FX / "tiny.jpg").read_bytes()
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", image_bytes, "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "solder bridging"})
    inv_id = resp.json()["id"]

    inv = client.get(f"/api/investigations/{inv_id}").json()
    assert inv["photo_url"]
    assert inv["photo_url"].startswith(f"/api/files/photos/{inv_id}")

    photo = client.get(inv["photo_url"])
    assert photo.status_code == 200
    assert photo.content == image_bytes


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


def test_demo_code_disabled_when_unset(client):
    """The fixture's TestClient already runs with DEMO_ACCESS_CODE unset (the repo's
    .env.example / local .env default) — every route must work with no header at
    all, exactly like local dev and the rest of this test module."""
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/complaints").status_code == 200
    assert client.get("/api/memory").status_code == 200


def test_demo_code_enforced_when_set(monkeypatch):
    from agent import main
    from agent.config import Settings
    from agent.events import bus

    async def fake_run_investigation(inv_id):
        await bus.publish(inv_id, "system", "done", "Investigation complete")
        bus.close(inv_id)

    monkeypatch.setattr(main, "run_investigation", fake_run_investigation)
    monkeypatch.setattr(main, "get_settings", lambda: Settings(demo_access_code="let-me-in"))
    client = TestClient(main.app)

    # /api/health never requires the code, even when one is configured.
    assert client.get("/api/health").status_code == 200

    # Every other /api/* route rejects a missing or wrong header...
    assert client.get("/api/complaints").status_code == 401
    assert client.get("/api/complaints", headers={"X-Demo-Code": "wrong"}).status_code == 401
    assert client.get("/api/memory", headers={"X-Demo-Code": "wrong"}).status_code == 401

    # ...and accepts the header when it matches.
    ok = client.get("/api/complaints", headers={"X-Demo-Code": "let-me-in"})
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)

    # EventSource/<img> can't set headers — the SSE stream and file routes also
    # accept the code as a query parameter.
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "x"},
                       headers={"X-Demo-Code": "let-me-in"})
    assert resp.status_code == 200
    inv_id = resp.json()["id"]

    no_code = client.get(f"/api/investigations/{inv_id}/events")
    assert no_code.status_code == 401

    with client.stream("GET", f"/api/investigations/{inv_id}/events?code=let-me-in") as stream:
        assert stream.status_code == 200
        assert stream.headers["content-type"].startswith("text/event-stream")
