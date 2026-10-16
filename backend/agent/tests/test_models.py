import pytest
from agent.config import Settings
from agent.models import Defect, Hypothesis, HypothesisResult, EightD, Investigation


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
