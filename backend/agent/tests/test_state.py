import pytest

from agent.models import Event, Investigation, MemoryEntry
from agent.state import MemoryStateStore, next_id


@pytest.fixture
def store():
    return MemoryStateStore()


def test_investigation_round_trips(store):
    inv = Investigation(id="inv_1", lot_id="L2611", status="running")
    store.save_investigation(inv)
    assert store.get_investigation("inv_1").lot_id == "L2611"


def test_unknown_investigation_returns_none(store):
    assert store.get_investigation("inv_nope") is None


def test_events_keep_their_order(store):
    for seq in range(3):
        store.append_event("inv_1", Event(seq=seq, ts="t", agent="system",
                                          type="step_started", title=f"s{seq}"))
    assert [e.seq for e in store.events("inv_1")] == [0, 1, 2]


def test_records_get_prefixed_sequential_ids(store):
    first = store.create_record("capa", {"summary": "a"})
    second = store.create_record("capa", {"summary": "b"})
    assert first.startswith("CAPA-") and second != first
    assert store.get_record("capa", first)["summary"] == "a"


def test_id_format_matches_the_demo_script():
    assert next_id("capa", start=142) == "CAPA-0142"
    assert next_id("work_order", start=412) == "WO-412"
    assert next_id("hold", start=77) == "H-77"


def test_memory_search_filters_by_defect_type(store):
    store.save_memory(MemoryEntry(id="m1", defect_type="solder_bridge",
                                  root_cause="reflow drift"), [1.0, 0.0])
    store.save_memory(MemoryEntry(id="m2", defect_type="tombstoning",
                                  root_cause="paste age"), [1.0, 0.0])
    hits = store.search_memory([1.0, 0.0], defect_type="solder_bridge", k=5)
    assert [m.id for m, _ in hits] == ["m1"]


def test_memory_search_ranks_by_similarity(store):
    store.save_memory(MemoryEntry(id="far", defect_type="x", root_cause="a"), [0.0, 1.0])
    store.save_memory(MemoryEntry(id="near", defect_type="x", root_cause="b"), [1.0, 0.0])
    hits = store.search_memory([1.0, 0.0], defect_type="x", k=2)
    assert hits[0][0].id == "near"
    assert hits[0][1] > hits[1][1]
