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


class TestArbitraryJudgeUploads:
    """A judge experimenting with the deployed prototype uploads whatever is on their
    laptop. `_prepare_for_model` is what stands between that and a model 400."""

    @staticmethod
    def _image(fmt: str, size=(40, 30), mode="RGB") -> bytes:
        import io

        from PIL import Image
        buf = io.BytesIO()
        Image.new(mode, size, "white").save(buf, format=fmt)
        return buf.getvalue()

    def test_a_gif_is_converted_to_jpeg_rather_than_rejected(self):
        """GIF is not in Gemini's accepted list. Failing on one would look like the
        vision step is broken rather than picky, so it is re-encoded even though it is
        well under the size threshold that would otherwise trigger a resize."""
        out_bytes, out_mime = vision_tool._prepare_for_model(self._image("GIF"), "image/gif")
        assert out_mime == "image/jpeg"
        assert out_bytes[:2] == b"\xff\xd8"          # JPEG SOI marker

    def test_a_palette_mode_gif_converts_without_raising(self):
        """Pillow cannot save mode "P" as JPEG at all -- this is the case the
        unconditional convert("RGB") exists for, and it is what a real GIF is."""
        out_bytes, out_mime = vision_tool._prepare_for_model(
            self._image("GIF", mode="P"), "image/gif")
        assert out_mime == "image/jpeg"
        assert out_bytes[:2] == b"\xff\xd8"

    def test_an_rgba_png_over_the_size_limit_converts_without_raising(self):
        """The other mode JPEG cannot hold. A screenshot with transparency, scaled."""
        big = self._image("PNG", size=(2000, 1200), mode="RGBA")
        out_bytes, out_mime = vision_tool._prepare_for_model(big, "image/png")
        assert out_mime == "image/jpeg"
        assert out_bytes[:2] == b"\xff\xd8"

    def test_a_small_png_is_left_exactly_as_it_arrived(self):
        """PNG is accepted and under the threshold: re-encoding it would lose quality
        for nothing."""
        png = self._image("PNG")
        assert vision_tool._prepare_for_model(png, "image/png") == (png, "image/png")

    def test_a_large_accepted_image_is_still_shrunk(self):
        from PIL import Image
        import io
        big = self._image("JPEG", size=(3000, 1500))
        out_bytes, out_mime = vision_tool._prepare_for_model(big, "image/jpeg")
        assert out_mime == "image/jpeg"
        assert max(Image.open(io.BytesIO(out_bytes)).size) == vision_tool.MAX_LONG_EDGE_PX

    def test_undecodable_bytes_pass_through_untouched(self):
        """Pillow has no HEIC support but Gemini does, so bytes we cannot open are
        better forwarded to a model that can read them than rejected here."""
        assert vision_tool._prepare_for_model(b"not-an-image", "image/heic") == (
            b"not-an-image", "image/heic")
