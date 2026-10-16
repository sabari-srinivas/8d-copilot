import json
from pathlib import Path

import pytest

from agent.models import Defect
from agent.tools import vision_tool

FX = Path(__file__).parent / "fixtures"


@pytest.fixture
def stub(monkeypatch):
    def _stub(fixture_name):
        payload = json.loads((FX / fixture_name).read_text())
        monkeypatch.setattr(vision_tool, "generate_structured",
                            lambda *a, **k: Defect.model_validate(payload))
        return payload
    return _stub


def test_defect_image_returns_a_typed_defect(stub):
    # vision_solder_bridge.json is a genuine recorded Gemini response for
    # data/images/defect_01.jpg -- NOT actually a solder bridge. The VisA pcb3
    # images are bent-lead/dislodged-component anomalies (see
    # data/images/IMAGES.md) and the vision prompt forbids guessing a cause, so
    # the recorded type reflects real model output, not the brief's filename.
    # This test checks the wiring (defect found -> typed, valid Defect), not a
    # specific defect type.
    payload = stub("vision_solder_bridge.json")
    d = vision_tool.analyze_defect_image((FX / "tiny.jpg").read_bytes(), "image/jpeg")
    assert d.type == payload["type"]
    assert d.type != "none"
    assert d.severity in ("critical", "major", "minor")
    assert 0.0 <= d.confidence <= 1.0
    assert len(d.visual_evidence) > 10


def test_clean_board_returns_none_type(stub):
    # vision_clean_board.json is a genuine recorded Gemini response for
    # data/images/no_defect_01.jpg, the VisA dataset's own "normal" board, taken
    # AFTER vision.md was tightened to explicitly list what does not count as a
    # defect (flux residue, dust, glare, normal tolerance) and to resolve
    # uncertainty toward `none`. Before that tightening this same image never
    # returned `none` across four live calls (see task-5-report.md); after it,
    # three straight calls all returned `none` at confidence 1.0, and this
    # fixture is one of them.
    payload = stub("vision_clean_board.json")
    d = vision_tool.analyze_defect_image((FX / "tiny.jpg").read_bytes(), "image/jpeg")
    assert d.type == "none"
    assert payload["type"] == "none"


def test_empty_image_bytes_raise_before_any_model_call():
    with pytest.raises(ValueError, match="empty image"):
        vision_tool.analyze_defect_image(b"", "image/jpeg")


def test_image_bytes_are_never_logged(caplog, stub):
    stub("vision_solder_bridge.json")
    with caplog.at_level("DEBUG"):
        vision_tool.analyze_defect_image(b"\xff\xd8\xff\xe0SECRETBYTES", "image/jpeg")
    assert "SECRETBYTES" not in caplog.text
