import asyncio

import pytest

from agent.events import EventBus


async def _take(bus, inv_id, n):
    out = []
    async for event in bus.subscribe(inv_id):
        out.append(event)
        if len(out) == n:
            break
    return out


@pytest.mark.asyncio
async def test_sequence_numbers_start_at_zero_and_increment():
    bus = EventBus()
    a = await bus.publish("inv_1", "system", "step_started", "a")
    b = await bus.publish("inv_1", "vision", "tool_result", "b")
    assert (a.seq, b.seq) == (0, 1)


@pytest.mark.asyncio
async def test_sequences_are_per_investigation():
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "a")
    other = await bus.publish("inv_2", "system", "step_started", "a")
    assert other.seq == 0


@pytest.mark.asyncio
async def test_a_late_subscriber_still_receives_the_history():
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "first")
    await bus.publish("inv_1", "vision", "tool_result", "second")
    got = await asyncio.wait_for(_take(bus, "inv_1", 2), timeout=2)
    assert [e.title for e in got] == ["first", "second"]


@pytest.mark.asyncio
async def test_a_live_subscriber_receives_new_events():
    bus = EventBus()
    task = asyncio.create_task(_take(bus, "inv_1", 1))
    await asyncio.sleep(0.05)
    await bus.publish("inv_1", "writer", "draft_ready", "ready")
    assert (await asyncio.wait_for(task, timeout=2))[0].title == "ready"


@pytest.mark.asyncio
async def test_two_subscribers_both_receive_every_event():
    bus = EventBus()
    tasks = [asyncio.create_task(_take(bus, "inv_1", 1)) for _ in range(2)]
    await asyncio.sleep(0.05)
    await bus.publish("inv_1", "system", "done", "done")
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)
    assert all(r[0].title == "done" for r in results)


@pytest.mark.asyncio
async def test_timestamps_are_utc_iso():
    bus = EventBus()
    event = await bus.publish("inv_1", "system", "done", "done")
    assert event.ts.endswith("Z") and "T" in event.ts


@pytest.mark.asyncio
async def test_close_ends_the_stream():
    bus = EventBus()
    await bus.publish("inv_1", "system", "done", "done")
    bus.close("inv_1")
    got = [e async for e in bus.subscribe("inv_1")]
    assert len(got) == 1


@pytest.mark.asyncio
async def test_an_event_published_during_replay_is_neither_lost_nor_duplicated():
    """The interleaving that a snapshot-then-register bus loses.

    `subscribe` yields history one event at a time, and every `yield` hands control back
    to the event loop. If the live queue is only registered *after* that replay loop
    finishes, anything the pipeline publishes while the consumer is still reading history
    goes nowhere: it is past the end of the snapshot and there is no queue to land in.
    Registering first risks the opposite fault — the same event arriving twice, once from
    the snapshot and once from the queue. Neither is acceptable.
    """
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "first")
    await bus.publish("inv_1", "vision", "tool_result", "second")

    async def consume():
        out = []
        async for event in bus.subscribe("inv_1"):
            out.append(event)
            if len(out) == 1:
                # The UI is still working through history; the pipeline publishes on.
                await bus.publish("inv_1", "writer", "draft_ready", "third")
            if len(out) == 3:
                break
        return out

    got = await asyncio.wait_for(consume(), timeout=2)
    assert [e.title for e in got] == ["first", "second", "third"]
    assert [e.seq for e in got] == [0, 1, 2]


@pytest.mark.asyncio
async def test_a_subscriber_that_arrives_after_the_run_finished_does_not_hang():
    """A completed run's history ends in `done`; replaying it must end the stream too,
    otherwise a late SSE connection waits forever for an event that will never come."""
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "started")
    await bus.publish("inv_1", "system", "done", "Investigation complete")
    got = await asyncio.wait_for(_collect(bus, "inv_1"), timeout=2)
    assert [e.type for e in got] == ["step_started", "done"]


async def _collect(bus, inv_id):
    return [e async for e in bus.subscribe(inv_id)]


@pytest.mark.asyncio
async def test_history_is_a_copy_and_is_also_written_to_the_state_store(monkeypatch):
    from agent.state import MemoryStateStore
    store = MemoryStateStore()
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "a")
    history = bus.history("inv_1")
    history.clear()
    assert len(bus.history("inv_1")) == 1
    assert [e.title for e in store.events("inv_1")] == ["a"]


@pytest.mark.asyncio
async def test_a_subscriber_that_stops_early_is_unregistered():
    """An SSE client that disconnects mid-run must not leave its queue behind to be
    filled for the life of the process. Starlette closes the generator on disconnect,
    which is what `aclose()` stands in for here."""
    bus = EventBus()
    stream = bus.subscribe("inv_1")
    task = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0.05)
    assert bus.subscriber_count("inv_1") == 1
    await bus.publish("inv_1", "system", "step_started", "a")
    assert (await asyncio.wait_for(task, timeout=2)).title == "a"
    await stream.aclose()
    assert bus.subscriber_count("inv_1") == 0
