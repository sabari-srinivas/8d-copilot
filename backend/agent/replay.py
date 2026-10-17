"""Replay a recorded investigation with no model calls.

Live mode is the default. `REPLAY_CASE=<name>` makes POST /api/investigations replay
`data/out/replay/<name>.json` instead of running the agents, so a recorded demo survives
a Vertex quota refusal mid-take.

Honesty: replay announces itself. GET /api/health reports `replay`, and the UI shows a
`Replay` chip in the header. A viewer must never be unsure whether a run is live.

Spacing comes from the recorded timestamps rather than a fixed interval. The real trace
pauses where the model was thinking; a flat delay looks obviously synthetic.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from agent.events import bus
from agent.models import Event, Investigation
from agent.state import get_state

log = logging.getLogger(__name__)

DIR = Path(__file__).resolve().parents[1] / "data" / "out" / "replay"
# A recorded gap longer than this is clamped — a run that stalled on a retry should not
# make the replay sit silently for a minute.
MAX_GAP_SECONDS = 12.0


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def gaps_from(events: list[Event]) -> list[float]:
    """Seconds to wait before each event, derived from the recorded timestamps.

    The first event fires immediately. Event timestamps are second-resolution, so bursts
    of same-second events come out as 0.0 and replay back-to-back, which is what the live
    stream does too.
    """
    out = [0.0]
    for previous, current in zip(events, events[1:]):
        a, b = _parse_ts(previous.ts), _parse_ts(current.ts)
        gap = (b - a).total_seconds() if a and b else 0.0
        out.append(min(max(gap, 0.0), MAX_GAP_SECONDS))
    return out


def record(inv_id: str, case_name: str) -> Path:
    """Write a finished investigation and its full event history to disk."""
    inv = get_state().get_investigation(inv_id)
    if inv is None:
        raise KeyError(f"no investigation {inv_id} to record")
    events = bus.history(inv_id)
    if not events:
        raise ValueError(f"investigation {inv_id} has no events to record")

    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{case_name}.json"
    path.write_text(json.dumps({
        "case": case_name,
        "recorded_from": inv_id,
        "investigation": inv.model_dump(),
        "events": [e.model_dump() for e in events],
    }, indent=2))
    log.info("recorded %d events from %s to %s", len(events), inv_id, path.name)
    return path


def load(case_name: str) -> tuple[Investigation, list[Event]]:
    """Read a recording. Raises FileNotFoundError naming the directory if absent."""
    path = DIR / f"{case_name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no replay recording {case_name!r} in {DIR}. "
            f"Record one with agent.replay.record(inv_id, {case_name!r}).")
    payload = json.loads(path.read_text())
    inv = Investigation.model_validate(payload["investigation"])
    events = [Event.model_validate(e) for e in payload["events"]]
    return inv, events


async def replay(case_name: str, inv_id: str) -> None:
    """Republish a recorded run under a new investigation id. No model calls."""
    inv, events = load(case_name)
    gaps = gaps_from(events)
    log.info("replaying %s as %s (%d events, %.1fs)",
             case_name, inv_id, len(events), sum(gaps))

    # Save the recorded state up front so GET /investigations/{id} answers while the
    # events are still streaming, exactly as a live run does.
    inv.id = inv_id
    state = get_state()
    await asyncio.to_thread(state.save_investigation, inv)

    try:
        for gap, event in zip(gaps, events):
            if gap:
                await asyncio.sleep(gap)
            await bus.publish(inv_id, event.agent, event.type, event.title,
                              detail=event.detail, data=event.data)
    finally:
        # The recording ends with `done`, so the stream is already terminal; close()
        # releases any subscriber still blocked if the replay was cut short.
        bus.close(inv_id)
