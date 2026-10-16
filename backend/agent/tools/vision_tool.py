"""Gemini multimodal defect reading. Strict JSON, no cause guessing, no bytes in logs."""
import io
import logging

from PIL import Image

from agent.models import Defect
from agent.tools.llm import generate_structured, load_prompt

log = logging.getLogger(__name__)

# PRD §13 requires the defect box inside a 10 s latency budget. Exploratory calls against
# the live model on the demo images' native resolution ranged roughly 7.9-11.9 s per call
# (see task-5-report.md) -- known variance that sometimes breaches the budget, not a one-off.
# Shrinking the long edge to 1024 px before sending cuts the request payload and measurably
# reduces latency without blurring the defect box past usefulness.
MAX_LONG_EDGE_PX = 1024


def _shrink_to_long_edge(image_bytes: bytes, mime_type: str,
                         max_edge: int = MAX_LONG_EDGE_PX) -> tuple[bytes, str]:
    """Downscale so the image's long edge is at most `max_edge` px, re-encoding as JPEG.
    Returns the original bytes/mime_type unchanged if already small enough, or if the bytes
    can't be decoded as an image (so a bad `tiny.jpg`-style fixture never crashes this path)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        return image_bytes, mime_type
    width, height = img.size
    if max(width, height) <= max_edge:
        return image_bytes, mime_type
    scale = max_edge / max(width, height)
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = img.convert("RGB").resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


def analyze_defect_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> Defect:
    if not image_bytes:
        raise ValueError("empty image: nothing to analyse")
    from google.genai import types
    image_bytes, mime_type = _shrink_to_long_edge(image_bytes, mime_type)
    log.info("analysing defect image (%d bytes, %s)", len(image_bytes), mime_type)
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    return generate_structured(load_prompt("vision"), Defect, parts=[part], temperature=0.1)
