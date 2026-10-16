"""One ordered event stream per investigation. History first, then live — so the UI can
subscribe after the POST returns and still see the whole run (PRD 12.3)."""
import asyncio
import itertools
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncIterator

from agent.models import Event
from agent.state import get_state

# Event types after which no further event is published for an investigation, so a
# stream that has delivered one can end rather than hold the connection open.
TERMINAL = ("done", "error")
# close() wakes blocked subscribers with this sentinel; it is never part of the history
# and never yielded. seq is negative so it can never collide with a real event.
_CLOSE_SENTINEL_SEQ = -1


class EventBus:
    def __init__(self):
        self._history: dict[str, list[Event]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._seq: dict[str, itertools.count] = defaultdict(lambda: itertools.count())
        self._closed: set[str] = set()

    async def publish(self, inv_id: str, agent: str, type: str, title: str,
                      detail: str = "", data: dict | None = None) -> Event:
        event = Event(seq=next(self._seq[inv_id]),
                      ts=datetime.now(timezone.utc).isoformat(timespec="seconds")
                        .replace("+00:00", "Z"),
                      agent=agent, type=type, title=title, detail=detail, data=data or {})
        # History then queues, with no await in between, so a subscriber can never
        # observe the event in one and miss it in the other.
        self._history[inv_id].append(event)
        get_state().append_event(inv_id, event)
        for queue in list(self._subscribers[inv_id]):
            queue.put_nowait(event)
        return event

    async def subscribe(self, inv_id: str) -> AsyncIterator[Event]:
        """Replay the history, then stream live events.

        Order matters. The queue is registered BEFORE the history is snapshotted, because
        every `yield` below hands control back to the event loop: if registration waited
        until the replay loop finished, an event published while the consumer was still
        reading history would be past the end of the snapshot with no queue to land in,
        and would be lost. Registering first means an event can in principle reach both
        the snapshot and the queue, so queued events at or below the last replayed
        sequence number are dropped — the stream yields each event exactly once.
        """
        queue: asyncio.Queue = asyncio.Queue()
        closed = inv_id in self._closed
        if not closed:
            self._subscribers[inv_id].append(queue)
        try:
            history = list(self._history[inv_id])
            last_seq = history[-1].seq if history else -1
            for event in history:
                yield event
            if closed or (history and history[-1].type in TERMINAL):
                return
            while True:
                event = await queue.get()
                if event.seq == _CLOSE_SENTINEL_SEQ:
                    return
                if event.seq <= last_seq:
                    continue          # already delivered from the history snapshot
                yield event
                if event.type in TERMINAL:
                    return
        finally:
            if queue in self._subscribers[inv_id]:
                self._subscribers[inv_id].remove(queue)

    def history(self, inv_id: str) -> list[Event]:
        return list(self._history[inv_id])

    def subscriber_count(self, inv_id: str) -> int:
        return len(self._subscribers[inv_id])

    def close(self, inv_id: str) -> None:
        self._closed.add(inv_id)
        for queue in list(self._subscribers[inv_id]):
            queue.put_nowait(Event(seq=_CLOSE_SENTINEL_SEQ, ts="", agent="system",
                                   type="done", title="closed"))


bus = EventBus()
