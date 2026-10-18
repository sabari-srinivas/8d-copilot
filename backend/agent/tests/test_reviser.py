"""agent/agents/reviser.py — the revise-not-redraft path (CR #14).

Only the model call is stubbed; the number-provenance check (agent/tools/provenance.py)
and the deterministic status rule run for real, exactly as in test_orchestrator.py's
golden-path tests for writer.run.
"""
import pytest

from agent.agents import reviser
from agent.events import bus
from agent.models import Complaint, Defect, EightD, EightDSection, HypothesisResult, Investigation
from agent.state import MemoryStateStore
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT

ORIGINAL_EIGHT_D = {
    "D1": {"text": "Team: SMT process engineer, quality engineer.", "citations": []},
    "D2": {"text": "Problem: solder bridging on lot L2612.", "citations": []},
    "D3": {"text": "Containment: lot L2612 held and re-inspected.", "citations": []},
    "D4": {"text": "Root cause: operator error. Operator OP-17 did not follow "
                   "procedure.", "citations": []},
    "D5": {"text": "Corrective action: OP-17 retrained.", "citations": []},
    "D6": {"text": "Verification: no further bridging observed.", "citations": []},
    "D7": {"text": "Prevent recurrence: training records updated.", "citations": []},
    "D8": {"text": "Closure: corrective action closed.", "citations": []},
}


def _rejection_complaint() -> Complaint:
    return Complaint(
        complaint_id="C-2026-033", customer="Hoshino Denso (fictional)", product="ECU-PCB-7",
        lot_id="L2612", defect="solder_bridge", is_rejection=True,
        objection="root cause stated as operator error; not acceptable",
        original_eight_d=ORIGINAL_EIGHT_D)


def _inv_with_supported_result() -> Investigation:
    return Investigation(
        id="inv_1", lot_id=GOLDEN_LOT, hold_lots=list(DRIFT_LOT_IDS),
        defect=Defect(type="solder_bridge", severity="major", box=[0, 0, 1, 1],
                     confidence=0.9, visual_evidence="Bridge between two pads."),
        results=[HypothesisResult(
            hypothesis_id="H2", verdict="supported", test="Welch t-test", p_value=0.0004,
            effect="+7.2 °C mean reflow peak temp", effect_value=7.2, effect_unit="°C",
            n_defect=6, n_good=58)])


def _revised_section(text: str) -> EightDSection:
    return EightDSection(text=text, citations=[])


@pytest.fixture
def wired_bus(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr("agent.state.get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    return store


@pytest.mark.asyncio
async def test_revised_draft_replaces_operator_error_with_the_real_cause(monkeypatch, wired_bus):
    """The hard constraint: when the objection IS that the original blamed operator
    error, the revision must not carry that sentence forward."""
    good_d4 = _revised_section(
        "Root cause: following work order WO-388, reflow peak temperature drifted "
        "above the profile limit across the affected lots, causing bridging "
        "[PFMEA row 14].")
    blank = _revised_section("Carried forward.")
    monkeypatch.setattr(reviser, "generate_structured", lambda *a, **k: reviser.WriterOutput(
        status="draft_ready",
        eight_d=EightD(D1=blank, D2=blank, D3=blank, D4=good_d4, D5=blank, D6=blank,
                       D7=blank, D8=blank)))

    out = await reviser.run("inv_r1", _inv_with_supported_result(), _rejection_complaint())
    assert out.status == "draft_ready"
    assert "operator error" not in out.eight_d.D4.text.lower()
    assert "WO-388" in out.eight_d.D4.text
    bus.close("inv_r1")


@pytest.mark.asyncio
async def test_revise_events_are_published_under_the_reviser_agent_name(monkeypatch, wired_bus):
    """The live trace must show this as its own step (CR #14's distinct-path shape),
    not folded into 'writer'."""
    blank = _revised_section("x")
    monkeypatch.setattr(reviser, "generate_structured", lambda *a, **k: reviser.WriterOutput(
        status="draft_ready",
        eight_d=EightD(**{f"D{i}": blank for i in range(1, 9)})))

    await reviser.run("inv_r2", _inv_with_supported_result(), _rejection_complaint())
    events = bus.history("inv_r2")
    assert any(e.agent == "reviser" and e.type == "step_started" for e in events)
    assert any(e.agent == "reviser" and e.type == "draft_ready" for e in events)
    bus.close("inv_r2")


@pytest.mark.asyncio
async def test_no_supported_hypothesis_does_not_revise_toward_a_cause(monkeypatch, wired_bus):
    inv = _inv_with_supported_result()
    inv.results[0].verdict = "inconclusive"
    monkeypatch.setattr(reviser, "generate_structured", lambda *a, **k: reviser.WriterOutput(
        status="insufficient_evidence", eight_d=None))
    out = await reviser.run("inv_2", inv, _rejection_complaint())
    assert out.status == "insufficient_evidence"
    assert out.eight_d is None
    assert out.missing_data
    bus.close("inv_2")


@pytest.mark.asyncio
async def test_an_invented_number_in_the_revision_is_flagged(monkeypatch, wired_bus):
    """The number-provenance check (ENGINEERING_RULES.md rule 4) still runs on a revision."""
    blank = _revised_section("x")
    bad = _revised_section("Peak temperature rose by 99.9 °C [PFMEA row 14].")
    monkeypatch.setattr(reviser, "generate_structured", lambda *a, **k: reviser.WriterOutput(
        status="draft_ready",
        eight_d=EightD(D1=blank, D2=blank, D3=blank, D4=bad, D5=blank, D6=blank,
                       D7=blank, D8=blank)))

    await reviser.run("inv_3", _inv_with_supported_result(), _rejection_complaint())
    events = bus.history("inv_3")
    errors = [e for e in events if e.type == "error"]
    assert errors, "an invented number must raise a provenance warning"
    assert "99.9" in errors[0].detail
    bus.close("inv_3")
