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
    assert golden["is_rejection"] is False


def test_six_closed_complaints_populate_past_investigations(client):
    """The original historical closed complaint (C-2026-024) plus the five seeded by
    data.constants.PAST_INVESTIGATIONS (see data/generate_plant.py and
    agent/tools/seed_past_investigations.py) -- the Complaints sidebar's "Past
    investigations" group."""
    rows = client.get("/api/complaints").json()
    closed = [c for c in rows if c["status"] == "closed"]
    assert len(closed) == 6
    from data.constants import PAST_INVESTIGATIONS
    closed_lots = {c["lot_id"] for c in closed}
    for entry in PAST_INVESTIGATIONS:
        assert entry["lot_id"] in closed_lots


def test_five_open_complaints_two_are_rejections_with_an_original_8d(client):
    """CR #6/#14: the contract's GET /complaints response for a rejection row."""
    rows = client.get("/api/complaints").json()
    open_rows = [c for c in rows if c["status"] == "open"]
    assert len(open_rows) == 5
    rejections = [c for c in open_rows if c["is_rejection"]]
    assert len(rejections) == 2
    for c in rejections:
        assert c["objection"]
        assert c["original_eight_d"] is not None
        assert set(c["original_eight_d"]) == {f"D{i}" for i in range(1, 9)}


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


def test_percent_encoded_traversal_is_blocked_with_a_plain_404(client):
    """The deployed service runs --allow-unauthenticated and this route is public, so
    a traversal here is a real file-read vulnerability, not a theoretical one.
    Verified exploitable before the fix: Starlette decodes `%2e%2e` to `..` while
    routing `/api/files/{key:path}`, which survives all the way into
    get_local_path's `key` argument -- a plain `../` in the URL would already have
    been normalised by then, but the percent-encoded form is not. This hits the
    route with the literal percent-encoded string (not a pre-decoded one) to prove
    the fix holds at the actual HTTP boundary an attacker would use, and asserts 404
    specifically -- not 400 -- because a blocked traversal attempt must be
    indistinguishable from an ordinary miss."""
    resp = client.get("/api/files/%2e%2e/%2e%2e/%2e%2e/pyproject.toml")
    assert resp.status_code == 404


def test_creating_an_investigation_accepts_an_optional_voice_note(client):
    """CR #12: voice_note is a third optional upload, alongside traveler, on the same
    endpoint -- proves the multipart field is wired through without needing a live
    model call (run_investigation itself is stubbed by the `client` fixture)."""
    resp = client.post(
        "/api/investigations",
        files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg"),
               "voice_note": ("note.wav", b"RIFF-fake-wav-bytes", "audio/wav")},
        data={"complaint_id": "C-2026-031", "lot_id": "L2611",
              "complaint_text": "solder bridging"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


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


def test_dashboard_summary_matches_the_seeded_dataset(client):
    body = client.get("/api/dashboard/summary").json()
    assert body["first_pass_yield"]["units"] == 31973
    assert body["first_pass_yield"]["defects"] == 282
    assert body["first_pass_yield"]["pct"] == 99.12
    assert body["open_eight_ds"]["count"] == 5
    assert body["charts"]["defect_pareto"] == {"solder_bridge": 188, "other": 94}
    assert body["charts"]["defect_rate_by_line"]["line2_avg_pct"] > \
        body["charts"]["defect_rate_by_line"]["line1_avg_pct"]
    assert len(body["charts"]["spc_reflow_peak"]["points"]) == 64
    assert body["charts"]["spc_reflow_peak"]["limit_c"] == 250.0


def test_capas_endpoint_surfaces_the_historical_capa_and_its_verdict(client):
    # The `client` fixture builds a bare TestClient without entering it as a context
    # manager, so FastAPI's lifespan (which seeds CAPA-0098 in production/local-dev)
    # never runs here -- seed directly, the same thing lifespan does on startup,
    # against the app's real (unmocked) global state.
    from agent.tools.capa_check import seed_historical_capa
    from agent.tools.memory import seed_historical_quality_memory
    seed_historical_capa()
    seed_historical_quality_memory()

    rows = client.get("/api/capas").json()
    hist = next(c for c in rows if c["id"] == "CAPA-0098")
    assert hist["effectiveness"]["verdict"] == "never_worked"
    assert hist["defect_type"] == "tombstoning"


def test_plant_lots_endpoint_returns_all_64_lots(client):
    rows = client.get("/api/plant/lots").json()
    assert len(rows) == 64
    assert "reflow_peak_temp_c" in rows[0]


def test_plant_maintenance_endpoint_returns_all_work_orders(client):
    rows = client.get("/api/plant/maintenance").json()
    assert len(rows) == 10
    assert {r["line"] for r in rows} == {"L1", "L2"}


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


def test_demo_code_does_not_block_cors_preflight(monkeypatch):
    """A cross-origin fetch() with a custom header (X-Demo-Code) triggers a browser
    CORS preflight first — a bare OPTIONS request that never carries the header
    itself, since the whole point of preflight is asking permission before sending
    it. require_demo_code must let OPTIONS through unconditionally so CORSMiddleware
    (registered before it, but placed OUTSIDE it in the actual call chain by
    FastAPI's insert(0) middleware ordering) can answer the preflight with proper
    CORS headers. Before this was fixed, every cross-origin gated call's preflight
    got a 401 with no CORS headers at all, which a browser would treat as a blocked
    request — found live when the frontend was pointed directly at the Cloud Run
    origin instead of going through the same-origin Firebase rewrite."""
    from agent.config import Settings
    from agent import main

    monkeypatch.setattr(main, "get_settings", lambda: Settings(demo_access_code="let-me-in"))
    client = TestClient(main.app)

    resp = client.options(
        "/api/complaints",
        headers={
            "Origin": "https://d-copilot-2026.web.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-demo-code",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"
    assert "x-demo-code" in resp.headers.get("access-control-allow-headers", "").lower()


class TestVoiceTranscribeEndpoint:
    """CR #15 -- the preview call the live microphone recorder makes the moment the
    speaker stops, so the transcript is on screen before anyone starts an investigation."""

    @staticmethod
    def _stub_note(monkeypatch, **overrides):
        from agent import main
        from agent.models import VoiceNote
        note = VoiceNote(language="ta-IN", language_name="Tamil",
                         transcript="லைன் ரெண்டுல ப்ரிட்ஜிங்",
                         translation="Bridging on line two",
                         lot_or_line="line 2", observations=["bridging on line 2"],
                         maintenance_mentions=[], low_confidence_fields=[], **overrides)
        monkeypatch.setattr(main, "analyze_voice_note", lambda *a, **k: note)
        return note

    def test_returns_the_full_voice_note_shape_the_ui_renders(self, client, monkeypatch):
        self._stub_note(monkeypatch)
        res = client.post("/api/voice/transcribe",
                          files={"audio": ("note.webm", b"fake-audio", "audio/webm")})
        assert res.status_code == 200
        body = res.json()
        # Every field the recorder panel reads. A missing one renders as blank, not as
        # an error, so the contract is asserted here rather than noticed in the demo.
        assert body["language_name"] == "Tamil"
        assert body["transcript"]
        assert body["translation"] == "Bridging on line two"
        assert body["lot_or_line"] == "line 2"
        assert body["observations"] == ["bridging on line 2"]
        assert body["maintenance_mentions"] == []
        assert body["low_confidence_fields"] == []

    def test_the_browsers_codecs_parameter_reaches_the_tool_unmangled(
            self, client, monkeypatch):
        """Chrome posts `audio/webm;codecs=opus`. The endpoint must pass the content
        type straight through and let voice_tool normalise it -- one choke point."""
        from agent import main
        seen = {}

        def capture(audio_bytes, mime_type="audio/wav"):
            seen["mime"] = mime_type
            return self._stub_note(monkeypatch)

        monkeypatch.setattr(main, "analyze_voice_note", capture)
        client.post("/api/voice/transcribe",
                    files={"audio": ("n.webm", b"x", "audio/webm;codecs=opus")})
        assert seen["mime"] == "audio/webm;codecs=opus"

    def test_an_unreadable_container_is_a_400_naming_the_format_not_a_500(
            self, client, monkeypatch):
        """The recorder shows this message verbatim, so it has to say which format
        failed -- a bare 500 would leave the user with nothing to act on."""
        from agent import main

        def refuse(*a, **k):
            raise ValueError("unsupported audio format 'audio/amr'")

        monkeypatch.setattr(main, "analyze_voice_note", refuse)
        res = client.post("/api/voice/transcribe",
                          files={"audio": ("n.amr", b"x", "audio/amr")})
        assert res.status_code == 400
        assert "audio/amr" in res.json()["detail"]

    def test_empty_audio_is_rejected_as_a_400(self, client):
        """A recording stopped before it started yields a zero-byte blob."""
        res = client.post("/api/voice/transcribe",
                          files={"audio": ("n.webm", b"", "audio/webm")})
        assert res.status_code == 400

    def test_transcribing_starts_no_investigation(self, client, monkeypatch):
        """The endpoint is a dead end by design: it writes no state, so a judge
        experimenting with the microphone cannot litter the inbox with half-runs."""
        from agent.state import MemoryStateStore, get_state
        self._stub_note(monkeypatch)
        store = get_state()
        # `get_state()` is a process-wide singleton and earlier tests in this file post
        # to /api/investigations, so the store is not empty here -- the claim is that
        # transcribing adds nothing, which is a before/after comparison, not emptiness.
        # Typed explicitly so a renamed attribute fails loudly instead of passing via a
        # getattr default.
        assert isinstance(store, MemoryStateStore)
        before_ids = set(store._inv)
        before_complaints = len(client.get("/api/complaints").json())

        client.post("/api/voice/transcribe",
                    files={"audio": ("n.webm", b"x", "audio/webm")})

        assert set(store._inv) == before_ids
        assert len(client.get("/api/complaints").json()) == before_complaints
