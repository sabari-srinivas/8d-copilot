"""The PRD §8 golden path as an automated test.

Only the LLM-backed steps are stubbed — vision, the investigator's proposal, the writer's
draft, the complaint parse and the document retrieval (which needs an embedding call).
The statistics, the plant data, the comparison groups and the event bus are the real
thing, so the four verdicts below are produced by scipy against the real dataset.
"""
import json
from pathlib import Path

import pytest

from agent import orchestrator
from agent.agents import evidence as evidence_agent
from agent.agents import intake as intake_agent
from agent.agents import investigator as inv_agent
from agent.agents import writer as writer_agent
from agent.events import bus
from agent.models import (Complaint, Defect, EightD, EightDSection, Hypothesis, Passage)
from agent.state import MemoryStateStore
from agent.tools.doc_search import chunk_documents
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT

FX = Path(__file__).parent / "fixtures"

HYPOTHESES = [
    Hypothesis(id="H1", category="Machine", text="Stencil wear increased paste deposit",
               parameter="stencil_print_count", direction="higher"),
    Hypothesis(id="H2", category="Machine",
               text="Reflow peak temperature drifted up on Line 2 after WO-388",
               parameter="reflow_peak_temp_c", event_wo_id="WO-388", direction="higher"),
    Hypothesis(id="H3", category="Environment", text="Room humidity caused paste slump",
               parameter="room_humidity_pct", direction="higher"),
    Hypothesis(id="H4", category="Man", text="A different operator ran the defect lots",
               parameter="operator_id", direction="higher"),
]

COMPLAINT = Complaint(
    complaint_id="C-2026-031", customer="Hoshino Denso (fictional)", product="ECU-PCB-7",
    lot_id=GOLDEN_LOT, defect="solder_bridge", qty_affected=14, qty_shipped=500,
    received="2026-10-15", eight_d_due="2026-10-29", due_in_working_days=10,
    text="Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units at our "
         "incoming/ICT. Please contain immediately and send 8D within 10 working days.")


def _corpus_passages() -> list[Passage]:
    """Real chunks from the real quality documents — retrieval is stubbed, the evidence
    is not. chunk_documents() reads the markdown files and needs no embedding call."""
    wanted = [("pfmea.md", "Row 14"), ("control_plan.md", "Item 6"), ("pfmea.md", "Row 9")]
    by_ref = {(c.source, c.ref): c for c in chunk_documents()}
    return [by_ref[key].model_copy(update={"score": 0.8 - i * 0.05})
            for i, key in enumerate(wanted)]


@pytest.fixture
def wired(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr("agent.state.get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(orchestrator, "get_state", lambda: store)
    defect = Defect.model_validate(json.loads((FX / "vision_solder_bridge.json").read_text()))
    monkeypatch.setattr("agent.agents.vision.analyze_defect_image", lambda *a, **k: defect)
    monkeypatch.setattr(intake_agent, "parse_complaint", lambda *a, **k: COMPLAINT)
    monkeypatch.setattr(inv_agent, "generate_structured",
                        lambda *a, **k: inv_agent.HypothesisList(hypotheses=HYPOTHESES))
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [])
    monkeypatch.setattr(evidence_agent, "search_quality_docs",
                        lambda *a, **k: _corpus_passages())
    section = EightDSection(text="Verified by Welch t-test [Chart: reflow peak temp by lot].")
    monkeypatch.setattr(writer_agent, "generate_structured", lambda *a, **k:
                        writer_agent.WriterOutput(status="draft_ready",
                                                  eight_d=EightD(**{f"D{i}": section
                                                                    for i in range(1, 9)})))
    return store


async def _run(**overrides) -> str:
    kwargs = dict(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                  image_bytes=(FX / "tiny.jpg").read_bytes(), mime_type="image/jpeg",
                  complaint_text="solder bridging")
    kwargs.update(overrides)
    inv_id = await orchestrator.start(**kwargs)
    await orchestrator.run_investigation(inv_id)
    return inv_id


@pytest.mark.asyncio
async def test_golden_path_reaches_draft_ready(wired):
    inv = wired.get_investigation(await _run())
    assert inv.status == "draft_ready"


@pytest.mark.asyncio
async def test_required_verdicts_hold_end_to_end(wired):
    verdicts = {r.hypothesis_id: r.verdict for r in wired.get_investigation(await _run()).results}
    assert verdicts["H2"] == "supported"
    assert verdicts["H1"] == "rejected"
    assert verdicts["H3"] == "rejected"
    assert verdicts["H4"] == "inconclusive"


@pytest.mark.asyncio
async def test_rejected_hypotheses_stay_in_the_state(wired):
    """PRD 17: rejected cards must stay visible — the answer to 'it's theatre'."""
    inv = wired.get_investigation(await _run())
    assert len(inv.results) == 4
    assert sum(1 for r in inv.results if r.verdict == "rejected") == 2


@pytest.mark.asyncio
async def test_hold_lots_are_the_defect_lots(wired):
    assert sorted(wired.get_investigation(await _run()).hold_lots) == sorted(DRIFT_LOT_IDS)


@pytest.mark.asyncio
async def test_four_actions_are_proposed(wired):
    kinds = {a.kind for a in wired.get_investigation(await _run()).proposed_actions}
    assert kinds == {"capa", "hold", "work_order", "customer_reply"}


@pytest.mark.asyncio
async def test_a_clean_board_ends_in_insufficient_evidence(wired, monkeypatch):
    clean = Defect.model_validate(json.loads((FX / "vision_clean_board.json").read_text()))
    monkeypatch.setattr("agent.agents.vision.analyze_defect_image", lambda *a, **k: clean)
    inv = wired.get_investigation(await _run())
    assert inv.status == "insufficient_evidence"
    assert inv.missing_data


@pytest.mark.asyncio
async def test_the_event_stream_tells_the_whole_story(wired):
    inv_id = await _run()
    types = [e.type for e in bus.history(inv_id)]
    assert types[-1] == "done"
    assert types.count("hypothesis_result") == 4
    assert "draft_ready" in types
    assert [e.seq for e in bus.history(inv_id)] == list(range(len(types)))


# --- task-9 review findings ---------------------------------------------------------


@pytest.mark.asyncio
async def test_event_data_matches_the_ui_contract(wired):
    """docs/contract/README.md pins the `data` shape per event type, and the UI switches
    on `type` exhaustively. Extra keys are fine (mock_events.json seq 8 mixes them in);
    a missing documented key is not."""
    inv_id = await _run()
    required = {"tool_call": {"tool", "args"}, "tool_result": {"tool", "summary"},
                "memory_hit": {"id", "defect_type", "root_cause"},
                "hypothesis": {"id", "category", "text", "direction"},
                "hypothesis_result": {"hypothesis_id", "verdict", "p_value", "effect"},
                "citation": {"label", "source", "ref"},
                "draft_ready": {"status"}, "error": {"message"}}
    for event in bus.history(inv_id):
        assert required.get(event.type, set()) <= set(event.data), \
            f"seq {event.seq} ({event.type}) is missing contract keys"
        if event.type in ("step_started", "done"):
            assert event.data == {}


@pytest.mark.asyncio
async def test_the_pending_profile_check_is_surfaced_as_its_own_card(wired):
    """The escape point of the whole case: a maintenance event whose post-check was never
    closed out. Found by reading post_check, not by naming a work order."""
    inv_id = await _run()
    cards = [e for e in bus.history(inv_id)
             if e.data.get("tool") == "get_maintenance_events"]
    assert [c.data["wo_id"] for c in cards] == ["WO-388"]
    assert "pending" in cards[0].data["post_check"]


@pytest.mark.asyncio
async def test_hypothesis_ids_are_renumbered_whatever_the_model_sent(wired, monkeypatch):
    """The UI's hypothesis cards and the 8D's cross-references key off H1..Hn. A prompt
    instruction is not a guarantee, so the code renumbers regardless."""
    invented = [h.model_copy(update={"id": f"{h.parameter}_h{i}"})
                for i, h in enumerate(HYPOTHESES, 1)]
    monkeypatch.setattr(inv_agent, "generate_structured",
                        lambda *a, **k: inv_agent.HypothesisList(hypotheses=invented))
    inv = wired.get_investigation(await _run())
    assert [h.id for h in inv.hypotheses] == ["H1", "H2", "H3", "H4"]
    assert [r.hypothesis_id for r in inv.results] == ["H1", "H2", "H3", "H4"]


@pytest.mark.asyncio
async def test_no_supported_hypothesis_ends_in_insufficient_evidence(wired, monkeypatch):
    """Deterministic Python decides this, not the writer: with nothing supported there is
    no verified root cause, so there is no 8D to sign."""
    nothing_supported = [h for h in HYPOTHESES if h.id != "H2"]
    monkeypatch.setattr(inv_agent, "generate_structured",
                        lambda *a, **k: inv_agent.HypothesisList(hypotheses=nothing_supported))
    inv = wired.get_investigation(await _run())
    assert inv.status == "insufficient_evidence"
    assert inv.missing_data
    assert inv.eight_d is None
    assert inv.proposed_actions == []
    assert len(inv.results) == 3, "rejected and inconclusive results still stay in the state"


@pytest.mark.asyncio
async def test_the_models_own_status_string_is_ignored(wired, monkeypatch):
    """Observed live: the model returned a complete, provenance-clean 8D under a status
    string that was not `draft_ready`, stranding the run in insufficient_evidence. The
    status is decided from the verdicts, never read off the model's reply."""
    section = EightDSection(text="Verified by Welch t-test [Chart: reflow peak temp by lot].")
    monkeypatch.setattr(writer_agent, "generate_structured", lambda *a, **k:
                        writer_agent.WriterOutput(status="Draft Ready",
                                                  eight_d=EightD(**{f"D{i}": section
                                                                    for i in range(1, 9)})))
    inv = wired.get_investigation(await _run())
    assert inv.status == "draft_ready"
    assert inv.eight_d is not None


@pytest.mark.asyncio
async def test_a_model_that_declines_to_draft_does_not_claim_draft_ready(wired, monkeypatch):
    monkeypatch.setattr(writer_agent, "generate_structured", lambda *a, **k:
                        writer_agent.WriterOutput(status="draft_ready", eight_d=None))
    inv = wired.get_investigation(await _run())
    assert inv.status == "insufficient_evidence"
    assert inv.missing_data


@pytest.mark.asyncio
async def test_citations_cover_the_top_hits_as_a_set(wired):
    """Measured retrieval margins are thin, so the evidence screen shows several cards
    rather than betting on one document ranking first."""
    inv = wired.get_investigation(await _run())
    refs = {(c.source, c.ref) for c in inv.citations}
    assert ("pfmea.md", "Row 14") in refs
    assert ("control_plan.md", "Item 6") in refs
    labels = {c.label for c in inv.citations}
    assert "PFMEA row 14" in labels
    assert "Control plan item 6" in labels
    assert any(c.source == "chart" for c in inv.citations), "the chart must be citable"


@pytest.mark.asyncio
async def test_upload_bytes_are_released_on_success(wired):
    inv_id = await _run()
    assert inv_id not in orchestrator._uploads


@pytest.mark.asyncio
async def test_upload_bytes_are_released_on_failure(wired, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("the model is down")
    monkeypatch.setattr(inv_agent, "generate_structured", boom)
    inv_id = await orchestrator.start(
        complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
        image_bytes=(FX / "tiny.jpg").read_bytes(), mime_type="image/jpeg",
        complaint_text="solder bridging")
    with pytest.raises(RuntimeError, match="the model is down"):
        await orchestrator.run_investigation(inv_id)
    assert inv_id not in orchestrator._uploads
    assert [e.type for e in bus.history(inv_id)][-2:] == ["error", "done"]


@pytest.mark.asyncio
async def test_no_image_bytes_reach_the_event_stream(wired):
    """PRD: no image bytes or secrets in logs or events."""
    inv_id = await _run()
    for event in bus.history(inv_id):
        blob = json.dumps(event.model_dump())
        assert "image_bytes" not in blob
        assert "\\u00ff" not in blob          # the JPEG marker bytes, had they leaked


@pytest.mark.asyncio
async def test_the_draft_is_provenance_clean(wired):
    """No `error` event from the number-provenance pass on the golden-path draft."""
    inv_id = await _run()
    errors = [e for e in bus.history(inv_id) if e.type == "error"]
    assert errors == []
