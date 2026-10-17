import json
from pathlib import Path

import pytest

from agent.models import VoiceNote
from agent.tools import voice_tool

FX = Path(__file__).parent / "fixtures"


@pytest.fixture
def stub(monkeypatch):
    def _stub(fixture_name):
        payload = json.loads((FX / fixture_name).read_text())
        monkeypatch.setattr(voice_tool, "generate_structured",
                            lambda *a, **k: VoiceNote.model_validate(payload))
        return payload
    return _stub


def test_clean_extraction_returns_a_typed_voice_note(stub):
    # voice_note_clean.json is a genuine recorded Gemini response for
    # data/audio/shift_lead_line2_en.wav (synthesised shift-lead remark, see
    # data/audio/AUDIO.md) -- the one live call made for this task, pasted verbatim
    # into the fixture. See voice-intake-report.md for the full live-call record.
    payload = stub("voice_note_clean.json")
    note = voice_tool.analyze_voice_note(b"RIFF-fake-wav-bytes", "audio/wav")
    assert note.language_name == "English"
    assert "line two" in note.lot_or_line
    assert note.observations == payload["observations"]
    assert note.maintenance_mentions
    assert note.low_confidence_fields == []
    assert note.transcript == note.translation      # already English


def test_unclear_lot_number_is_flagged_low_confidence(stub):
    # Hand-authored fixture (not a live call): a mumbled lot number must come back
    # flagged, never silently guessed (CR #12).
    stub("voice_note_low_confidence.json")
    note = voice_tool.analyze_voice_note(b"fake audio bytes", "audio/wav")
    assert "lot_or_line" in note.low_confidence_fields
    assert note.lot_or_line      # still filled in with a best guess...
    assert "unclear" in note.lot_or_line or "xx" in note.lot_or_line  # ...visibly uncertain


def test_non_english_note_carries_both_transcript_and_translation(stub):
    # Hand-authored fixture: a Tamil note (CR #12's JAPAC case) must report which
    # language it heard, keep the original-script transcript, and still translate.
    payload = stub("voice_note_tamil.json")
    note = voice_tool.analyze_voice_note(b"fake tamil audio bytes", "audio/wav")
    assert note.language == "ta-IN"
    assert note.language_name == "Tamil"
    assert note.transcript == payload["transcript"]
    assert note.transcript != note.translation
    assert "line 2" in note.translation.lower() or "line 2" in note.lot_or_line.lower()
    assert "oven" in note.translation.lower()


def test_empty_audio_bytes_raise_before_any_model_call():
    with pytest.raises(ValueError, match="empty audio"):
        voice_tool.analyze_voice_note(b"", "audio/wav")


def test_audio_bytes_are_never_logged(caplog, stub):
    stub("voice_note_clean.json")
    with caplog.at_level("DEBUG"):
        voice_tool.analyze_voice_note(b"RIFF\x00\x00SECRETAUDIOBYTES", "audio/wav")
    assert "SECRETAUDIOBYTES" not in caplog.text
