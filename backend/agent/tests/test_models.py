from datetime import date

import pytest
from agent.config import Settings
from agent.models import Complaint, Defect, Hypothesis, HypothesisResult, EightD, Investigation, Event


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
        "running", "draft_ready", "approved", "insufficient_evidence", "failed"}


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
        "intake", "vision", "investigator", "evidence", "writer", "reviser", "system"}


def test_event_type_values_are_the_contract_values():
    assert set(Event.model_fields["type"].annotation.__args__) == {
        "step_started", "tool_call", "tool_result", "memory_hit", "hypothesis",
        "hypothesis_result", "citation", "draft_ready", "done", "error",
        "capa_effectiveness"}


def test_event_rejects_unknown_type():
    with pytest.raises(ValueError):
        Event(seq=0, ts="2026-10-16T10:02:00.000Z", agent="system", type="bogus", title="x")


def test_event_rejects_unknown_agent():
    with pytest.raises(ValueError):
        Event(seq=0, ts="2026-10-16T10:02:00.000Z", agent="bogus", type="done", title="x")


def _complaint(received, eight_d_due):
    return Complaint(complaint_id="C-x", customer="x", product="x", lot_id="L1",
                     defect="x", received=received, eight_d_due=eight_d_due)


@pytest.mark.parametrize("nullish", ["null", "NULL", "None", "n/a", "N/A", "na",
                                     "NA", "-", "unknown", "Unknown", "  null  "])
def test_complaint_blanks_out_nullish_text_in_date_fields(nullish):
    c = _complaint(nullish, nullish)
    assert c.received == ""
    assert c.eight_d_due == ""


def test_complaint_maps_real_none_to_empty_string():
    c = _complaint(None, None)
    assert c.received == ""
    assert c.eight_d_due == ""


def test_complaint_leaves_a_real_date_alone():
    c = _complaint("2026-10-15", "2026-10-29")
    assert c.received == "2026-10-15"
    assert c.eight_d_due == "2026-10-29"


def test_complaint_rejection_fields_default_to_a_new_defect_report():
    c = _complaint("2026-10-15", "2026-10-29")
    assert c.is_rejection is False
    assert c.objection == ""
    assert c.original_eight_d is None


def test_complaint_can_carry_a_rejected_8d():
    section = {"text": "Root cause: operator error.", "citations": []}
    c = Complaint(complaint_id="C-x", customer="x", product="x", lot_id="L1", defect="x",
                 is_rejection=True, objection="root cause stated as operator error; not acceptable",
                 original_eight_d={f"D{i}": section for i in range(1, 9)})
    assert c.is_rejection is True
    assert "operator error" in c.objection
    assert EightD.model_validate(c.original_eight_d).D4.text == "Root cause: operator error."


@pytest.mark.parametrize("nullish", ["null", None, "none", "n/a", "-", "unknown"])
def test_complaint_eight_d_due_never_parses_as_neither_date_nor_empty(nullish):
    """The contract the validator must uphold: eight_d_due is either a real
    ISO date or an empty string -- never a string date.fromisoformat chokes on."""
    c = _complaint("2026-10-15", nullish)
    if c.eight_d_due == "":
        return
    date.fromisoformat(c.eight_d_due)  # must not raise
