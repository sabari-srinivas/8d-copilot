"""The only place a Gemini client is constructed. Model IDs come from env, never from code."""
import logging
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agent.config import get_settings

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """The model failed schema validation twice (PRD 9.5)."""


def load_prompt(name: str) -> str:
    path = PROMPTS / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"no prompt named {name!r} at {path}")
    return path.read_text()


@lru_cache
def _client():
    from google import genai
    s = get_settings()
    return genai.Client(vertexai=True, project=s.gcp_project,
                        location=s.vertex_region or s.gcp_region)


def _raw_generate(*, prompt: str, parts: list | None, schema: dict | None,
                  temperature: float) -> str:
    from google.genai import types
    s = get_settings()
    config = types.GenerateContentConfig(temperature=temperature)
    if schema:
        config.response_mime_type = "application/json"
        config.response_schema = schema
    contents = [*(parts or []), prompt]
    resp = _client().models.generate_content(
        model=s.require_model(), contents=contents, config=config)
    return resp.text


def generate_structured(prompt: str, schema: type[T], *, parts: list | None = None,
                        temperature: float = 0.2) -> T:
    """One retry on validation failure, then raise (PRD 9.5)."""
    last: Exception | None = None
    attempt_prompt = prompt
    for attempt in (1, 2):
        text = _raw_generate(prompt=attempt_prompt, parts=parts,
                             schema=schema.model_json_schema(), temperature=temperature)
        try:
            return schema.model_validate_json(text)
        except ValidationError as exc:
            # Pydantic v2's model_validate_json raises ValidationError (not
            # json.JSONDecodeError) for malformed JSON too, so one except clause
            # covers both "not JSON" and "JSON but wrong shape".
            last = exc
            # Log the error, never the payload — it may contain image-derived content.
            log.warning("structured output failed validation (attempt %d): %s",
                        attempt, exc.__class__.__name__)
            attempt_prompt = (f"{prompt}\n\nYour previous reply did not match the schema "
                              f"({exc.__class__.__name__}). Reply with valid JSON only.")
    raise StructuredOutputError(f"{schema.__name__} validation failed twice") from last


def generate_text(prompt: str, *, temperature: float = 0.3) -> str:
    return _raw_generate(prompt=prompt, parts=None, schema=None, temperature=temperature)


def embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    resp = _client().models.embed_content(model=s.require_embed_model(), contents=texts)
    return [e.values for e in resp.embeddings]
