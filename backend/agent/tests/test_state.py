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


def test_save_record_uses_the_given_id_not_the_counter(store):
    """save_record (unlike create_record) writes under a caller-chosen id and must
    never advance the live CAPA-0142... counter -- the seeding use case
    (agent/tools/capa_check.seed_historical_capa)."""
    store.save_record("capa", "CAPA-0098", {"summary": "historical"})
    assert store.get_record("capa", "CAPA-0098")["summary"] == "historical"
    live = store.create_record("capa", {"summary": "live"})
    assert live == "CAPA-0142"


def test_list_records_returns_everything_of_one_kind(store):
    store.save_record("capa", "CAPA-0098", {"summary": "historical"})
    store.create_record("capa", {"summary": "live"})
    store.create_record("hold", {"lots": ["L1"]})
    ids = {r["id"] for r in store.list_records("capa")}
    assert ids == {"CAPA-0098", "CAPA-0142"}
    assert len(store.list_records("hold")) == 1


def test_list_records_empty_for_an_unused_kind(store):
    assert store.list_records("capa") == []


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
