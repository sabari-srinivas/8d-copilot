import pytest
from agent.config import Settings
from agent.models import Defect, Hypothesis, HypothesisResult, EightD, Investigation, Event


def test_model_name_must_come_from_env():
    s = Settings(gemini_model="")
    with pytest.raises(RuntimeError, match="never hard-coded"):
        s.require_model()


def test_defect_box_is_four_fractions():
    d = Defect(type="solder_bridge", severity="major", box=[0.1, 0.2, 0.3, 0.1],
               confidence=0.86, visual_evidence="Bright metal bridge between two fine-pitch pads.")
    assert len(d.box) == 4
    assert all(0.0 <= v <= 1.0 for v in d.box)


def test_defect_rejects_unknown_type():
    with pytest.raises(ValueError):
        Defect(type="banana", severity="major", box=[0, 0, 1, 1],
               confidence=0.5, visual_evidence="x")


def test_hypothesis_requires_a_parameter_or_an_event():
    with pytest.raises(ValueError, match="parameter or event"):
        Hypothesis(id="H9", category="Method", text="Something vague", direction="higher")


def test_investigation_statuses_are_the_contract_values():
    assert set(Investigation.model_fields["status"].annotation.__args__) == {
        "running", "draft_ready", "approved", "insufficient_evidence"}


def test_eight_d_has_all_eight_sections():
    assert [f for f in EightD.model_fields] == [f"D{i}" for i in range(1, 9)]


def test_hypothesis_result_verdicts_are_the_contract_values():
    assert set(HypothesisResult.model_fields["verdict"].annotation.__args__) == {
        "supported", "rejected", "inconclusive"}


def test_event_round_trips_a_representative_event():
    e = Event(seq=11, ts="2026-10-16T10:02:06.600Z", agent="investigator",
              type="hypothesis_result", title="H2 supported",
              detail="Welch t-test, defect lots vs good lots",
              data={"hypothesis_id": "H2", "verdict": "supported", "p_value": 0.0001})
    assert e.seq == 11
    assert e.agent == "investigator"
    assert e.type == "hypothesis_result"
    assert e.data["hypothesis_id"] == "H2"


def test_event_agent_values_are_the_contract_values():
    assert set(Event.model_fields["agent"].annotation.__args__) == {
        "intake", "vision", "investigator", "evidence", "writer", "system"}


def test_event_type_values_are_the_contract_values():
    assert set(Event.model_fields["type"].annotation.__args__) == {
        "step_started", "tool_call", "tool_result", "memory_hit", "hypothesis",
        "hypothesis_result", "citation", "draft_ready", "done", "error"}


def test_event_rejects_unknown_type():
    with pytest.raises(ValueError):
        Event(seq=0, ts="2026-10-16T10:02:00.000Z", agent="system", type="bogus", title="x")


def test_event_rejects_unknown_agent():
    with pytest.raises(ValueError):
        Event(seq=0, ts="2026-10-16T10:02:00.000Z", agent="bogus", type="done", title="x")
