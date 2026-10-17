"""Replay must reproduce a recorded run without touching a model."""
import asyncio
import json

import pytest

from agent import replay as replay_mod
from agent.events import EventBus
from agent.models import Event, Investigation
from agent.state import MemoryStateStore


def _event(seq: int, ts: str, type: str = "tool_result", title: str = "t") -> Event:
    return Event(seq=seq, ts=ts, agent="system", type=type, title=title)


def test_gaps_come_from_the_recorded_timestamps_not_a_fixed_interval():
    events = [_event(0, "2026-10-17T10:00:00Z"),
              _event(1, "2026-10-17T10:00:00Z"),      # same second -> back to back
              _event(2, "2026-10-17T10:00:07Z")]      # a real 7s model pause
    assert replay_mod.gaps_from(events) == [0.0, 0.0, 7.0]


def test_a_stalled_gap_is_clamped_so_replay_never_sits_silent():
    events = [_event(0, "2026-10-17T10:00:00Z"), _event(1, "2026-10-17T10:05:00Z")]
    assert replay_mod.gaps_from(events)[1] == replay_mod.MAX_GAP_SECONDS


def test_a_malformed_timestamp_degrades_to_no_wait_rather_than_crashing():
    events = [_event(0, "not-a-timestamp"), _event(1, "2026-10-17T10:00:03Z")]
    assert replay_mod.gaps_from(events) == [0.0, 0.0]


def test_a_missing_recording_names_the_directory_and_how_to_make_one():
    with pytest.raises(FileNotFoundError, match="nope"):
        replay_mod.load("nope")


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    """A recording on disk, with every in-memory trace of it removed afterwards."""
    monkeypatch.setattr(replay_mod, "DIR", tmp_path)
    inv = Investigation(id="inv_source", lot_id="L2611", status="draft_ready",
                       photo_url="/api/files/photos/inv_source.jpg")
    events = [_event(0, "2026-10-17T10:00:00Z", "step_started", "Investigation started"),
              _event(1, "2026-10-17T10:00:00Z", "tool_result", "Solder bridge · Major"),
              _event(2, "2026-10-17T10:00:01Z", "draft_ready", "8D draft ready"),
              _event(3, "2026-10-17T10:00:01Z", "done", "Investigation complete")]
    (tmp_path / "golden.json").write_text(json.dumps({
        "case": "golden", "recorded_from": "inv_source",
        "investigation": inv.model_dump(),
        "events": [e.model_dump() for e in events]}))
    return tmp_path


@pytest.mark.asyncio
async def test_replay_reconstitutes_state_and_events_under_a_new_id(recorded, monkeypatch):
    """The cold-process case: nothing but the file on disk."""
    store = MemoryStateStore()
    bus = EventBus()
    monkeypatch.setattr(replay_mod, "get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(replay_mod, "bus", bus)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)   # keep the test fast

    await replay_mod.replay("golden", "inv_new")

    stored = store.get_investigation("inv_new")
    assert stored is not None, "replay must save the recorded state under the new id"
    assert stored.lot_id == "L2611"
    assert stored.status == "draft_ready"

    types = [e.type for e in bus.history("inv_new")]
    assert types == ["step_started", "tool_result", "draft_ready", "done"]
    assert [e.seq for e in bus.history("inv_new")] == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_replay_makes_no_model_call(recorded, monkeypatch):
    """Any reach for a Gemini client during replay is a failure."""
    store = MemoryStateStore()
    bus = EventBus()
    monkeypatch.setattr(replay_mod, "get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(replay_mod, "bus", bus)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)

    def explode(*args, **kwargs):
        raise AssertionError("replay must not call a model")

    monkeypatch.setattr("agent.tools.llm._client", explode)
    monkeypatch.setattr("agent.tools.llm._raw_generate", explode)
    monkeypatch.setattr("agent.tools.llm.embed", explode)

    await replay_mod.replay("golden", "inv_new")
    assert [e.type for e in bus.history("inv_new")][-1] == "done"


@pytest.mark.asyncio
async def test_a_late_subscriber_still_sees_the_whole_replayed_run(recorded, monkeypatch):
    """The UI subscribes after the POST returns, so it is always late."""
    store = MemoryStateStore()
    bus = EventBus()
    monkeypatch.setattr(replay_mod, "get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(replay_mod, "bus", bus)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)

    await replay_mod.replay("golden", "inv_new")

    seen = [e async for e in bus.subscribe("inv_new")]
    assert [e.type for e in seen] == ["step_started", "tool_result", "draft_ready", "done"]


@pytest.mark.asyncio
async def test_replay_uses_the_recordings_photo_url_when_nothing_was_uploaded_live(
        recorded, monkeypatch):
    """Cold-process case: no prior start() call under this id (e.g. a server restart
    mid-replay-setup), so there is nothing live to preserve -- the recording's own
    photo_url is the only one available and must be used."""
    store = MemoryStateStore()
    bus = EventBus()
    monkeypatch.setattr(replay_mod, "get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(replay_mod, "bus", bus)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)

    await replay_mod.replay("golden", "inv_new")

    assert store.get_investigation("inv_new").photo_url == "/api/files/photos/inv_source.jpg"


@pytest.mark.asyncio
async def test_replay_preserves_the_live_uploads_photo_url_over_the_recordings(
        recorded, monkeypatch):
    """The real path: orchestrator.start() already saved an Investigation for inv_id
    carrying the photo_url of the image the viewer just uploaded (saved through the
    live files backend). Under Cloud Run the recording's own photo_url points at a
    file excluded from the image, so replay must keep the live upload's photo_url
    rather than overwrite it with the recording's -- otherwise the hero defect photo
    renders as a grey box during the one mode that exists to survive a quota outage."""
    store = MemoryStateStore()
    bus = EventBus()
    monkeypatch.setattr(replay_mod, "get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(replay_mod, "bus", bus)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)

    live_upload = Investigation(id="inv_new", lot_id="L2611", status="running",
                                photo_url="/api/files/photos/inv_new.jpg")
    store.save_investigation(live_upload)

    await replay_mod.replay("golden", "inv_new")

    stored = store.get_investigation("inv_new")
    assert stored.photo_url == "/api/files/photos/inv_new.jpg"
    assert stored.status == "draft_ready"      # the rest of the state is still the recording's


@pytest.mark.asyncio
async def test_main_run_pops_uploaded_bytes_in_replay_mode(monkeypatch):
    """`_uploads` (orchestrator.py) holds the raw uploaded image bytes for a run's
    lifetime. On the live path, run_investigation's own finally pops it -- but
    replay() never calls run_investigation, so main._run's replay branch has to pop
    it itself, or a full copy of every replayed upload's bytes sits in memory for
    the rest of the process's life. This drives the real committed golden replay
    recording (data/out/replay/golden.json) through main._run end to end and checks
    the dict afterwards."""
    from agent import main
    from agent.orchestrator import _uploads

    inv_id = "inv_replay_leak_check"
    _uploads[inv_id] = {"image": b"x" * 10, "mime": "image/jpeg",
                        "complaint_text": "", "traveler": None}

    fake_settings = type("FakeSettings", (), {"replay_case": "golden"})()
    monkeypatch.setattr(main, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(replay_mod, "MAX_GAP_SECONDS", 0.0)   # keep the test fast

    await main._run(inv_id)

    assert inv_id not in _uploads


def test_recording_an_unknown_investigation_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(replay_mod, "DIR", tmp_path)
    monkeypatch.setattr(replay_mod, "get_state", lambda: MemoryStateStore())
    with pytest.raises(KeyError, match="inv_missing"):
        replay_mod.record("inv_missing", "golden")
