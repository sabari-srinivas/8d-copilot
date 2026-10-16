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
    """The contest rule and PRD 9.6: model names come only from env."""
    from pathlib import Path
    import re
    pattern = re.compile(r"gemini-[0-9a-z.\-]+|text-embedding-[0-9a-z.\-]+", re.I)
    root = Path(llm.__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{n}: {line.strip()}")
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
