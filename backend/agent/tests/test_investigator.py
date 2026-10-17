"""agent/agents/investigator.py's CAPA-effectiveness wiring: "similar past case found"
is not the same claim as "that case's fix worked". No live model calls -- every
LLM-backed and plant-data call the investigator makes is monkeypatched; the only thing
under test is whether `run()` calls verify_capa_effectiveness and publishes
`capa_effectiveness` exactly when a memory hit carries a usable capa_id/line/created.
"""
import pytest

from agent.agents import investigator as inv_agent
from agent.events import bus
from agent.models import CapaEffectiveness, Defect, Hypothesis, HypothesisResult, MemoryEntry

DEFECT = Defect(type="solder_bridge", severity="critical", box=[0.1, 0.1, 0.1, 0.1],
                confidence=0.9, visual_evidence="bridge near U7")

HYPOTHESES = [
    Hypothesis(id="H1", category="Machine", text="Reflow drift",
              parameter="reflow_peak_temp_c", direction="higher"),
    Hypothesis(id="H2", category="Material", text="Paste age too high",
              parameter="paste_age_h", direction="higher"),
    Hypothesis(id="H3", category="Environment", text="Humidity drove the defect",
              parameter="room_humidity_pct", direction="higher"),
]

RESULT = HypothesisResult(hypothesis_id="H1", verdict="supported", test="Welch t-test",
                          p_value=0.001, effect="+8 C mean peak temp", effect_value=8.0,
                          effect_unit="C", n_defect=6, n_good=50)

HIT = MemoryEntry(id="MEM-0098", defect_type="tombstoning",
                  root_cause="Paste past its working window", parameter="paste_age_h",
                  line="L1", capa_id="CAPA-0098", lot_id="L2389",
                  investigation_id="inv_hist_0024", created="2026-07-10T00:00:00+00:00")

EFFECTIVENESS = CapaEffectiveness(
    capa_id="CAPA-0098", defect_type="tombstoning", line="L1", implemented_on="2026-07-10",
    verdict="never_worked", p_value=0.48, effect="never actually fixed", effect_value=-0.0005,
    n_before=10, n_immediate=7, n_recent=7)


@pytest.fixture(autouse=True)
def _stub_llm_and_plant(monkeypatch):
    """Everything investigator.run() needs that is not the thing under test."""
    monkeypatch.setattr(inv_agent, "generate_structured",
                        lambda *a, **k: inv_agent.HypothesisList(hypotheses=HYPOTHESES))
    monkeypatch.setattr(inv_agent, "get_lot_genealogy",
                        lambda lot_id: {"line": "L2", "shift": "A"})
    monkeypatch.setattr(inv_agent, "get_process_window", lambda: {"n_lots": 10, "days": 30})
    monkeypatch.setattr(inv_agent, "get_maintenance_events", lambda line: [])
    monkeypatch.setattr(inv_agent, "test_hypothesis", lambda *a, **k: RESULT)


def _capa_events(inv_id):
    return [e for e in bus.history(inv_id) if e.type == "capa_effectiveness"]


@pytest.mark.asyncio
async def test_a_memory_hit_with_a_capa_triggers_the_effectiveness_check(monkeypatch):
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [HIT])
    monkeypatch.setattr(inv_agent, "verify_capa_effectiveness",
                        lambda *a, **k: EFFECTIVENESS)
    await inv_agent.run("inv_capa_wiring_1", "L2611", DEFECT)

    events = _capa_events("inv_capa_wiring_1")
    assert len(events) == 1
    assert events[0].data["capa_id"] == "CAPA-0098"
    assert events[0].data["verdict"] == "never_worked"
    # The capa_effectiveness card must follow its memory_hit, not precede it.
    types = [e.type for e in bus.history("inv_capa_wiring_1")]
    assert types.index("memory_hit") < types.index("capa_effectiveness")


@pytest.mark.asyncio
async def test_the_check_runs_with_the_hits_own_fields(monkeypatch):
    """Proves the wiring passes the memory hit's own capa_id/defect_type/line and the
    date portion of `created` through -- not hard-coded demo values."""
    captured = {}

    def fake_check(capa_id, defect_type, line, implemented_on):
        captured.update(capa_id=capa_id, defect_type=defect_type, line=line,
                        implemented_on=implemented_on)
        return EFFECTIVENESS

    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [HIT])
    monkeypatch.setattr(inv_agent, "verify_capa_effectiveness", fake_check)
    await inv_agent.run("inv_capa_wiring_2", "L2611", DEFECT)

    assert captured == {"capa_id": "CAPA-0098", "defect_type": "tombstoning",
                        "line": "L1", "implemented_on": "2026-07-10"}


@pytest.mark.asyncio
async def test_no_memory_hit_means_no_effectiveness_event(monkeypatch):
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [])
    called = []
    monkeypatch.setattr(inv_agent, "verify_capa_effectiveness",
                        lambda *a, **k: called.append(1))
    await inv_agent.run("inv_capa_wiring_3", "L2611", DEFECT)

    assert called == []
    assert _capa_events("inv_capa_wiring_3") == []


@pytest.mark.asyncio
async def test_a_memory_hit_without_a_capa_id_does_not_trigger_the_check(monkeypatch):
    """A confirmed cause can be saved with no CAPA raised against it (only a hold or a
    work order approved) -- there is nothing to verify in that case."""
    no_capa = HIT.model_copy(update={"capa_id": ""})
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [no_capa])
    called = []
    monkeypatch.setattr(inv_agent, "verify_capa_effectiveness",
                        lambda *a, **k: called.append(1))
    await inv_agent.run("inv_capa_wiring_4", "L2611", DEFECT)

    assert called == []
    assert _capa_events("inv_capa_wiring_4") == []


@pytest.mark.asyncio
async def test_a_memory_hit_without_a_line_does_not_trigger_the_check(monkeypatch):
    no_line = HIT.model_copy(update={"line": ""})
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [no_line])
    called = []
    monkeypatch.setattr(inv_agent, "verify_capa_effectiveness",
                        lambda *a, **k: called.append(1))
    await inv_agent.run("inv_capa_wiring_5", "L2611", DEFECT)

    assert called == []
    assert _capa_events("inv_capa_wiring_5") == []
