"""Gemini multimodal defect reading. Strict JSON, no cause guessing, no bytes in logs."""
import io
import logging

from PIL import Image

from agent.models import Defect
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.media_types import image_needs_reencoding

log = logging.getLogger(__name__)

# PRD §13 requires the defect box inside a 10 s latency budget. Exploratory calls against
# the live model on the demo images' native resolution ranged roughly 7.9-11.9 s per call
# (see task-5-report.md) -- known variance that sometimes breaches the budget, not a one-off.
# Shrinking the long edge to 1024 px before sending cuts the request payload and measurably
# reduces latency without blurring the defect box past usefulness.
MAX_LONG_EDGE_PX = 1024

# Task 15c measurement: 3 runs each of defect_03.jpg and no_defect_01.jpg at temperature
# 0.0 came back fully consistent (3/3 solder_bridge, 3/3 none), an improvement over the
# "majority-stable" (2/3) reads documented at 0.1 in test_vision_tool.py. This is a pure
# classification task with a schema-constrained output, so there is no case for sampling
# diversity -- lower temperature should only help, and measurement confirmed it did.
VISION_TEMPERATURE = 0.0


def _prepare_for_model(image_bytes: bytes, mime_type: str,
                       max_edge: int = MAX_LONG_EDGE_PX) -> tuple[bytes, str]:
    """Get an arbitrary upload into something Gemini accepts, at a sane size.

    Two independent reasons to re-encode, either of which is enough:

    * the long edge is over `max_edge` px (latency, see above), or
    * the type is one the model rejects -- GIF, BMP, TIFF and friends. A judge
      experimenting with the deployed prototype uploads whatever is on their laptop, and
      failing on a GIF would look like the vision step is broken rather than picky. Only
      PNG/JPEG/WEBP/HEIC/HEIF survive untouched (`media_types.GEMINI_IMAGE_TYPES`).

    Returns the original bytes and type when neither applies, or when the bytes can't be
    decoded as an image at all -- a bad `tiny.jpg`-style fixture must not crash this path,
    and an undecodable HEIC (Pillow has no HEIC support, but Gemini does) is better passed
    through to a model that can read it than rejected here.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        return image_bytes, mime_type
    width, height = img.size
    too_big = max(width, height) > max_edge
    unsupported = image_needs_reencoding(mime_type)
    if not too_big and not unsupported:
        return image_bytes, mime_type
    if too_big:
        scale = max_edge / max(width, height)
        img = img.resize((max(1, round(width * scale)), max(1, round(height * scale))),
                         Image.LANCZOS)
    buf = io.BytesIO()
    # `convert("RGB")` last, and unconditionally: a palette GIF or an RGBA PNG cannot be
    # saved as JPEG without it, and the resize above preserves whatever mode it started in.
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


def analyze_defect_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> Defect:
    if not image_bytes:
        raise ValueError("empty image: nothing to analyse")
    from google.genai import types
    image_bytes, mime_type = _prepare_for_model(image_bytes, mime_type)
    log.info("analysing defect image (%d bytes, %s)", len(image_bytes), mime_type)
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    return generate_structured(load_prompt("vision"), Defect, parts=[part],
                               temperature=VISION_TEMPERATURE)
