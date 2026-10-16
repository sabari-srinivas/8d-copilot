"""The only place a Gemini client is constructed. Model IDs come from env, never from code."""
import logging
import threading
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agent.config import get_settings

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """The model failed schema validation twice (PRD 9.5)."""


# Task 10's threading fix runs intake and vision concurrently via asyncio.to_thread, so
# this is the first code path in the app where two threads can call _client() at once.
# A bare @lru_cache does NOT serialize the wrapped call itself (only the cache dict
# bookkeeping) — two threads racing on a cold cache both construct their own
# genai.Client, and the loser's instance is dropped and garbage-collected as soon as its
# single in-flight call returns, which closes its own httpx client via Client.__del__.
# Observed live, reproducibly, on a freshly started server: the very first investigation
# after a cold start intermittently raised "Cannot send a request, as the client has
# been closed." A plain threading.Lock with double-checked locking makes construction
# happen exactly once, with every other caller blocking on the lock until it's ready
# rather than racing to build a second, short-lived client.
_client_lock = threading.Lock()
_client_instance = None


def load_prompt(name: str) -> str:
    path = PROMPTS / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"no prompt named {name!r} at {path}")
    return path.read_text()


def _client():
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:          # still None after acquiring the lock
                from google import genai
                s = get_settings()
                _client_instance = genai.Client(vertexai=True, project=s.gcp_project,
                                                location=s.vertex_region or s.gcp_region)
    return _client_instance


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
