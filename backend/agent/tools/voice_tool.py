"""Gemini multimodal voice-note reading. Strict JSON, no audio bytes in logs.

CR #12: a shift lead's recorded remark, read the same way `vision_tool.py` reads a
photo -- bytes in, one `generate_structured` call, a validated Pydantic model out.
Gemini handles audio natively through Vertex AI, no separate speech-to-text step, and
reads Tamil (`ta-IN`) and Hindi (`hi-IN`) as readily as English -- the JAPAC answer to
"a Tier-2 supplier has no MES": not even a spreadsheet, just a shift lead talking.
"""
import logging

from agent.models import VoiceNote
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.media_types import normalize_audio_mime

log = logging.getLogger(__name__)

# Transcription/extraction, not creative writing -- same reasoning as vision_tool's
# VISION_TEMPERATURE: a schema-constrained reading task has no case for sampling
# diversity, so the lowest temperature should only help.
VOICE_TEMPERATURE = 0.0


def analyze_voice_note(audio_bytes: bytes, mime_type: str = "audio/wav") -> VoiceNote:
    if not audio_bytes:
        raise ValueError("empty audio: nothing to transcribe")
    from google.genai import types
    # A live browser recording arrives as `audio/webm;codecs=opus` (Chrome, Firefox) or
    # `audio/mp4` (Safari). The model rejects the parameterised string outright and has
    # never heard of `audio/mp4`, so both are mapped to a spelling it accepts before the
    # call -- the single choke point, the same way vision_tool re-encodes images.
    mime_type = normalize_audio_mime(mime_type)
    # Byte count and mime type only -- never the audio itself (CLAUDE.md rule 6),
    # exactly like vision_tool.analyze_defect_image's own log line.
    log.info("analysing voice note (%d bytes, %s)", len(audio_bytes), mime_type)
    part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    return generate_structured(load_prompt("voice"), VoiceNote, parts=[part],
                               temperature=VOICE_TEMPERATURE)
