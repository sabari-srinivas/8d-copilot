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
    inv = Investigation(id="inv_source", lot_id="L2611", status="draft_ready")
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


def test_recording_an_unknown_investigation_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(replay_mod, "DIR", tmp_path)
    monkeypatch.setattr(replay_mod, "get_state", lambda: MemoryStateStore())
    with pytest.raises(KeyError, match="inv_missing"):
        replay_mod.record("inv_missing", "golden")
