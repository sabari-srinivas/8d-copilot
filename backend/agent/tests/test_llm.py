import pytest
from pydantic import BaseModel

from agent.config import Settings
from agent.tools import llm


class Tiny(BaseModel):
    answer: str
    score: float


def test_prompts_load_from_disk():
    text = llm.load_prompt("vision")
    assert "solder_bridge" in text


def test_missing_prompt_raises_with_the_name():
    with pytest.raises(FileNotFoundError, match="nope"):
        llm.load_prompt("nope")


def test_no_model_id_is_hard_coded_anywhere_in_the_package():
    """CLAUDE.md rule 3: model names come only from env, in code, tests, comments or docs.

    Scans every .py and .md file under backend/ (not just agent/, and NOT skipping
    tests), excluding only .venv. The regex pattern below does not match its own literal
    source line (the bracket class breaks the match right after "gemini-"/"text-embedding-"),
    so this test legitimately scans itself without needing a self-exclusion.
    """
    import os
    import re
    from pathlib import Path
    pattern = re.compile(r"gemini-[0-9a-z.\-]+|text-embedding-[0-9a-z.\-]+", re.I)
    root = Path(llm.__file__).resolve().parents[2]  # backend/
    offenders = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".venv"]
        for fname in filenames:
            if not (fname.endswith(".py") or fname.endswith(".md")):
                continue
            path = Path(dirpath) / fname
            for n, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(root)}:{n}: {line.strip()}")
    assert not offenders, "hard-coded model IDs found:\n" + "\n".join(offenders)


def test_validation_failure_retries_once_then_raises(monkeypatch):
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        return '{"answer": "x"}'          # missing `score`, always invalid

    monkeypatch.setattr(llm, "_raw_generate", fake_call)
    monkeypatch.setattr(llm, "get_settings", lambda: Settings(gemini_model="test-model"))
    with pytest.raises(llm.StructuredOutputError):
        llm.generate_structured("hi", Tiny)
    assert calls["n"] == 2


def test_second_attempt_succeeding_returns_the_model(monkeypatch):
    seq = ['{"answer": "x"}', '{"answer": "x", "score": 0.5}']
    monkeypatch.setattr(llm, "_raw_generate", lambda **kw: seq.pop(0))
    monkeypatch.setattr(llm, "get_settings", lambda: Settings(gemini_model="test-model"))
    assert llm.generate_structured("hi", Tiny).score == 0.5


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeEmbedResponse:
    def __init__(self, vectors):
        self.embeddings = [_FakeEmbedding(v) for v in vectors]


class _FakeTextResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    """Stands in for `client.models` below `_client()`, so generate_text/embed are
    tested at their real wiring point (did they pass require_model()/require_embed_model()
    through?) rather than by stubbing _raw_generate, which would hide a wiring bug."""

    def __init__(self):
        self.generate_content_calls = []
        self.embed_content_calls = []

    def generate_content(self, *, model, contents, config):
        self.generate_content_calls.append({"model": model, "contents": contents})
        return _FakeTextResponse("a plain-text reply")

    def embed_content(self, *, model, contents):
        self.embed_content_calls.append({"model": model, "contents": contents})
        return _FakeEmbedResponse([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])


class _FakeClient:
    def __init__(self):
        self.models = _FakeModels()


def test_generate_text_is_wired_to_require_model_and_returns_a_string(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(llm, "_client", lambda: fake_client)
    monkeypatch.setattr(llm, "get_settings", lambda: Settings(gemini_model="test-text-model"))

    result = llm.generate_text("summarise this")

    assert result == "a plain-text reply"
    assert isinstance(result, str)
    assert fake_client.models.generate_content_calls[0]["model"] == "test-text-model"


def test_embed_is_wired_to_require_embed_model_and_returns_vectors(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(llm, "_client", lambda: fake_client)
    monkeypatch.setattr(llm, "get_settings", lambda: Settings(embed_model="test-embed-model"))

    result = llm.embed(["first passage", "second passage"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert isinstance(result, list) and all(isinstance(v, list) for v in result)
    assert fake_client.models.embed_content_calls[0]["model"] == "test-embed-model"
    assert fake_client.models.embed_content_calls[0]["contents"] == [
        "first passage", "second passage"]
