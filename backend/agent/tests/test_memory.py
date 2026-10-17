import pytest

from agent.state import MemoryStateStore
from agent.tools import memory as mem


@pytest.fixture(autouse=True)
def local(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr(mem, "get_state", lambda: store)
    # Deterministic pseudo-embeddings: same words -> same vector, no model call.
    monkeypatch.setattr(mem, "embed", lambda texts: [
        [float(t.lower().count(w)) for w in ("reflow", "temperature", "paste", "humidity")]
        for t in texts])
    return store


def test_saving_returns_an_id_and_lists_back():
    mid = mem.save_quality_memory(investigation_id="inv_1", defect_type="solder_bridge",
                                  root_cause="Reflow peak temperature drift after WO-388",
                                  parameter="reflow_peak_temp_c", line="L2",
                                  capa_id="CAPA-0142", lot_id="L2611")
    assert mid.startswith("MEM-")
    assert [e.root_cause for e in mem.list_quality_memory()] == [
        "Reflow peak temperature drift after WO-388"]


def test_similar_case_is_found_for_the_same_defect_type():
    mem.save_quality_memory(investigation_id="inv_1", defect_type="solder_bridge",
                            root_cause="Reflow peak temperature drift after WO-388",
                            parameter="reflow_peak_temp_c", line="L2",
                            capa_id="CAPA-0142", lot_id="L2611")
    hits = mem.search_quality_memory("solder_bridge", "reflow temperature too high", k=2)
    assert hits and hits[0].capa_id == "CAPA-0142"


def test_a_different_defect_type_does_not_match():
    mem.save_quality_memory(investigation_id="inv_1", defect_type="tombstoning",
                            root_cause="Paste past its working window",
                            parameter="paste_age_h", line="L1",
                            capa_id="CAPA-0098", lot_id="L2389")
    assert mem.search_quality_memory("solder_bridge", "reflow temperature too high") == []


def test_empty_memory_returns_empty_not_an_error():
    assert mem.search_quality_memory("solder_bridge", "anything") == []


def test_seeding_the_historical_capa_makes_it_findable():
    mid = mem.seed_historical_quality_memory()
    assert mid == mem.HISTORICAL_SEED_ID
    hits = mem.search_quality_memory("tombstoning", "tombstoning paste age")
    assert hits and hits[0].capa_id == "CAPA-0098" and hits[0].line == "L1"


def test_seeding_twice_is_a_no_op():
    first = mem.seed_historical_quality_memory()
    second = mem.seed_historical_quality_memory()
    assert first == mem.HISTORICAL_SEED_ID
    assert second is None
    assert len(mem.list_quality_memory()) == 1


def test_the_seeded_entry_never_collides_with_the_live_counter():
    """HISTORICAL_SEED_ID must not be something next_id("memory") could ever produce
    for a real approval -- see save_quality_memory's next_id("memory") call."""
    mem.seed_historical_quality_memory()
    live_id = mem.save_quality_memory(investigation_id="inv_1", defect_type="solder_bridge",
                                      root_cause="Reflow peak temperature drift",
                                      capa_id="CAPA-0142")
    assert live_id != mem.HISTORICAL_SEED_ID
    assert live_id == "MEM-0001"
