"""The only place a Gemini client is constructed. Model IDs come from env, never from code."""
import logging
import random
import threading
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agent.config import get_settings

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
T = TypeVar("T", bound=BaseModel)

# Transient-error retry, applied to every outbound call (generate_structured,
# generate_text, embed). Tunable in one place.
RETRY_ATTEMPTS = 3            # total tries, including the first; 2 retries after a failure
RETRY_BASE_DELAY_S = 1.0      # backoff: 1s, 2s, 4s, ... (RETRY_BASE_DELAY_S * 2**(attempt-1))
RETRY_JITTER_FRAC = 0.25      # +/-25% jitter on each delay
# Google surfaces 429/503/500 as retryable in its own client-library guidance; 400/401/403/404
# are bugs or config errors (bad request, bad auth, wrong resource) -- retrying those wastes
# the budget and hides the real problem, so they are raised immediately instead.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 503})


class StructuredOutputError(RuntimeError):
    """The model failed schema validation twice (PRD 9.5)."""


class TransientAPIError(RuntimeError):
    """A transient API error (429/500/503) survived every retry attempt."""


# Task 10's threading fix runs intake and vision concurrently via asyncio.to_thread, so
# this is the first code path in the app where two threads can call _client() at once.
# A bare @lru_cache does NOT serialize the wrapped call itself (only the cache dict
# bookkeeping) — two threads racing on a cold cache could each construct their own
# genai.Client. Observed live, reproducibly, on a freshly started server: the very first
# investigation after a cold start intermittently raised "Cannot send a request, as the
# client has been closed." The exact mechanism by which a second, momentarily-unused
# Client ends up closing a client in use was not isolated further; what is confirmed is
# that two Clients were being constructed on a cold start at all, which a plain
# threading.Lock with double-checked locking rules out — construction now happens
# exactly once, with every other caller blocking on the lock until it's ready rather
# than racing to build a second one. (Stress-probed with 16 threads released off a
# shared barrier: exactly one construction, no caller ever observes None.)
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


def _retry_delay(attempt: int) -> float:
    """attempt is 1-based (1 -> ~1s, 2 -> ~2s, 3 -> ~4s), before +/-RETRY_JITTER_FRAC jitter."""
    base = RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
    jitter = base * RETRY_JITTER_FRAC
    return base + random.uniform(-jitter, jitter)


def _call_with_retry(fn, /, *args, **kwargs):
    """Call `fn`, retrying up to RETRY_ATTEMPTS times with exponential backoff + jitter if it
    raises a transient google.genai API error (429/500/503). Any other ClientError/ServerError
    (400/401/403/404 and friends) is raised immediately on the first attempt -- see the module
    docstring constants for why. Imports google.genai.errors lazily so this module stays the
    only place that pulls in the (heavier) genai SDK at call time, not at import time.
    """
    from google.genai import errors as genai_errors
    last: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except (genai_errors.ClientError, genai_errors.ServerError) as exc:
            code = getattr(exc, "code", None)
            if code not in RETRYABLE_STATUS_CODES:
                raise
            last = exc
            if attempt == RETRY_ATTEMPTS:
                break
            delay = _retry_delay(attempt)
            # Log the error, never the payload (CLAUDE.md rule 6).
            log.warning(
                "transient API error, status %s (attempt %d/%d), retrying in %.2fs: %s",
                code, attempt, RETRY_ATTEMPTS, delay, exc.__class__.__name__)
            time.sleep(delay)
    raise TransientAPIError(
        f"giving up after {RETRY_ATTEMPTS} attempts: status {getattr(last, 'code', '?')}"
    ) from last


def _raw_generate(*, prompt: str, parts: list | None, schema: dict | None,
                  temperature: float) -> str:
    from google.genai import types
    s = get_settings()
    config = types.GenerateContentConfig(temperature=temperature)
    if schema:
        config.response_mime_type = "application/json"
        config.response_schema = schema
    contents = [*(parts or []), prompt]
    resp = _call_with_retry(_client().models.generate_content,
                            model=s.require_model(), contents=contents, config=config)
    return resp.text


def generate_structured(prompt: str, schema: type[T], *, parts: list | None = None,
                        temperature: float = 0.2) -> T:
    """One retry on validation failure, then raise (PRD 9.5).

    Each of these (at most 2) raw calls goes through _raw_generate -> _call_with_retry,
    which independently retries transient API errors up to RETRY_ATTEMPTS times. The two
    retry loops compose but stay bounded: worst case is 2 * RETRY_ATTEMPTS raw network
    calls (currently 2 * 3 = 6), not an open-ended product. A transient error that survives
    its own retry budget raises TransientAPIError, which is not a ValidationError, so it
    propagates straight out of this function rather than consuming a validation attempt.
    """
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
    resp = _call_with_retry(_client().models.embed_content,
                            model=s.require_embed_model(), contents=texts)
    return [e.values for e in resp.embeddings]
