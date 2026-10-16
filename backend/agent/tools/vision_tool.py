"""Gemini multimodal defect reading. Strict JSON, no cause guessing, no bytes in logs."""
import logging

from agent.models import Defect
from agent.tools.llm import generate_structured, load_prompt

log = logging.getLogger(__name__)


def analyze_defect_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> Defect:
    if not image_bytes:
        raise ValueError("empty image: nothing to analyse")
    from google.genai import types
    log.info("analysing defect image (%d bytes, %s)", len(image_bytes), mime_type)
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    return generate_structured(load_prompt("vision"), Defect, parts=[part], temperature=0.1)
