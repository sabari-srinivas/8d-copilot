import pytest

from agent.state import MemoryStateStore
from agent.tools import seed_past_investigations as seed_mod
from data.constants import PAST_INVESTIGATIONS


@pytest.fixture
def local_state(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr(seed_mod, "get_state", lambda: store)
    monkeypatch.setattr(seed_mod, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    return store


def test_seeds_one_capa_and_one_memory_entry_per_past_investigation(local_state):
    seeded = seed_mod.seed_past_investigations()
    assert seeded == [p["capa_id"] for p in PAST_INVESTIGATIONS]
    for entry in PAST_INVESTIGATIONS:
        capa = local_state.get_record("capa", entry["capa_id"])
        assert capa is not None
        assert capa["status"] == "closed"
        assert capa["lot_id"] == entry["lot_id"]
    memory_ids = {m.id for m, _ in local_state._memory}
    assert memory_ids == {p["memory_id"] for p in PAST_INVESTIGATIONS}


def test_memory_entries_link_back_to_their_capa(local_state):
    seed_mod.seed_past_investigations()
    by_id = {m.id: m for m, _ in local_state._memory}
    for entry in PAST_INVESTIGATIONS:
        mem = by_id[entry["memory_id"]]
        assert mem.capa_id == entry["capa_id"]
        assert mem.lot_id == entry["lot_id"]
        assert mem.line == entry["line"]


def test_seeding_twice_is_a_no_op(local_state):
    first = seed_mod.seed_past_investigations()
    second = seed_mod.seed_past_investigations()
    assert len(first) == 5
    assert second == []
    assert len(local_state.list_records("capa")) == 5


def test_ids_never_collide_with_the_live_counter_or_the_historical_capa(local_state):
    seed_mod.seed_past_investigations()
    live_id = local_state.create_record("capa", {"summary": "live"})
    assert live_id == "CAPA-0142"
    ids = {p["capa_id"] for p in PAST_INVESTIGATIONS}
    assert "CAPA-0098" not in ids
    assert "CAPA-0142" not in ids
