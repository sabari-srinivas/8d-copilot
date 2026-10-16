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
    # data/images/defect_03.jpg -- the golden-path solder-bridge demo image,
    # re-sourced here after prompt tuning (see task-5-report.md). Under the
    # final vision.md this image reads as solder_bridge in 2 of 3 live calls
    # (the third read none), so it is majority-stable, not unanimous; this
    # fixture is one genuine solder_bridge call, not an invented "ideal" one.
    payload = stub("vision_solder_bridge.json")
    d = vision_tool.analyze_defect_image((FX / "tiny.jpg").read_bytes(), "image/jpeg")
    assert d.type == "solder_bridge"
    assert payload["type"] == "solder_bridge"
    assert d.severity in ("critical", "major", "minor")
    assert 0.0 <= d.confidence <= 1.0
    assert len(d.visual_evidence) > 10


def test_clean_board_returns_none_type(stub):
    # vision_clean_board.json is a genuine recorded Gemini response for
    # data/images/no_defect_01.jpg, the VisA dataset's own "normal" board,
    # taken under the final vision.md (tightened to list what does not count
    # as a defect, and to distinguish "unsure of type" from "no anomaly at
    # all"). This image reads as none in 3 of 4 live calls under that prompt
    # (the fourth read misalignment) -- majority-stable, not unanimous.
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
