"""Cited passages from the quality documents.

local  : chunk data/docs/*.md on `## ` headings, embed with EMBED_MODEL, cosine similarity
vertex : Vertex AI RAG Engine corpus built by infra/build_rag.py
Both return the same Passage shape and both rank most-relevant-first, so the evidence
agent never knows which one ran. Passage.score is NOT comparable across backends: local
reports cosine similarity (higher is more relevant), vertex reports the RAG Engine's
native distance (lower is more relevant) — see the note in `_search_vertex`.
"""
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from agent.config import get_settings
from agent.models import Passage
from agent.tools.llm import embed

DOCS = Path(__file__).resolve().parents[2] / "data" / "docs"
MAX_QUOTE = 600


_TABLE_ROW = re.compile(r"^\|(.*)\|$")


def _depipe_table(body: str) -> str:
    """Render a markdown `| Field | Value |` table as `Field: Value Field: Value ...`,
    dropping the header row and separator rows like `|---|---|`."""
    fields = []
    for line in body.splitlines():
        line = line.strip()
        m = _TABLE_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if all(re.fullmatch(r"[-:\s]*", c) for c in cells):
            continue  # separator row, e.g. |---|---|
        if cells == ["Field", "Value"]:
            continue  # header row
        if len(cells) == 2:
            fields.append(f"{cells[0]}: {cells[1]}")
    return " ".join(fields)


def _prose_paragraph(body: str) -> str:
    """The clean prose paragraph in a section body (the 'Mechanism: ... Effect: ...'
    or 'Characteristic: ...' sentence for PFMEA/control-plan rows, or the whole
    narrative paragraph for past-8D sections, which have no table at all) —
    whichever paragraph is NOT the markdown table."""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if para and not para.startswith("|"):
            return " ".join(para.split())
    return ""


def _truncate_quote(text: str, limit: int = MAX_QUOTE) -> str:
    """Cap at `limit` chars, cutting on a word boundary and marking the cut with an
    ellipsis rather than slicing mid-word."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    budget = limit - 1  # reserve a char for the ellipsis
    cut = text.rfind(" ", 0, budget)
    if cut <= 0:
        cut = budget
    return text[:cut].rstrip(" ,;:.") + "…"


@lru_cache
def chunk_documents() -> tuple[Passage, ...]:
    chunks: list[Passage] = []
    for path in sorted(DOCS.glob("*.md")):
        text = path.read_text()
        parts = re.split(r"^## (.+)$", text, flags=re.M)
        # parts = [preamble, heading1, body1, heading2, body2, ...]
        for heading, body in zip(parts[1::2], parts[2::2]):
            quote = _truncate_quote(_prose_paragraph(body) or _depipe_table(body))
            if quote:
                chunks.append(Passage(source=path.name, ref=heading.strip(), quote=quote))
    return tuple(chunks)


@lru_cache
def _chunk_matrix() -> np.ndarray:
    chunks = chunk_documents()
    if not chunks:
        raise RuntimeError(f"no citable chunks found under {DOCS} — is the docs corpus empty?")
    vectors = embed([f"{c.source} {c.ref}: {c.quote}" for c in chunks])
    m = np.array(vectors, dtype="float32")
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def _search_local(query: str, k: int) -> list[Passage]:
    q = np.array(embed([query])[0], dtype="float32")
    q /= np.linalg.norm(q)
    scores = _chunk_matrix() @ q
    chunks = chunk_documents()
    return [chunks[i].model_copy(update={"score": round(float(scores[i]), 4)})
            for i in np.argsort(-scores)[:k]]


@lru_cache
def _init_vertex() -> None:
    import agentplatform
    s = get_settings()
    agentplatform.init(project=s.gcp_project, location=s.vertex_region or s.gcp_region)


def _search_vertex(query: str, k: int) -> list[Passage]:
    # Deprecated `vertexai.rag` is intentionally avoided here — this project's
    # installed SDK ships the non-deprecated `agentplatform.rag` client with an
    # identical call shape. Imported lazily so no test path ever loads it.
    from agentplatform import rag
    s = get_settings()
    _init_vertex()
    # Ask for more raw contexts than k: the corpus's chunk size is large enough
    # that one returned context routinely spans two or more `## ` headings
    # (confirmed against the live corpus — see infra/build_rag.py), and each
    # one is split back into its own Passage below, so k contexts does not
    # reliably yield k distinct citable refs. A generous multiplier also
    # reduces (does not eliminate) the chance that a relevant heading loses a
    # same-chunk tie-break against an irrelevant neighbour right at the cutoff.
    resp = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=s.rag_corpus)],
        text=query, rag_retrieval_config=rag.RagRetrievalConfig(top_k=max(k * 3, 8)))
    # NOTE on score direction: the RAG Engine's `score` field is a distance —
    # LOWER is more relevant — the opposite of the local backend's cosine
    # similarity (higher is more relevant). Confirmed empirically: requesting
    # larger top_k against the live corpus returns the same leading contexts
    # with monotonically increasing scores. Keep/sort by the *minimum* score
    # per heading here; do not negate or rescale it into a fake similarity.
    best: dict[tuple[str, str], Passage] = {}
    for i, ctx in enumerate(resp.contexts.contexts):
        source = Path(getattr(ctx, "source_uri", "") or "").name or "quality-docs"
        score = round(float(getattr(ctx, "score", 0.0)), 4)
        text = ctx.text or ""
        # The corpus strips the `## ` markdown prefix, leaving the heading
        # alone on its own line (e.g. "Row 14"), so split on that bare form.
        parts = re.split(r"(?m)^(Row \d+|Item \d+|D\d)\s*$", text)
        headings_found = False
        for heading, body in zip(parts[1::2], parts[2::2]):
            quote = _truncate_quote(body)
            if not quote:
                continue
            headings_found = True
            key = (source, heading.strip())
            if key not in best or score < best[key].score:
                best[key] = Passage(source=source, ref=heading.strip(), quote=quote, score=score)
        if not headings_found:
            # No recognisable heading landed in this chunk (e.g. a chunk that
            # is entirely a dangling continuation) — keep it, citable by
            # source only, rather than silently dropping retrieved evidence.
            # Key by (source, context index) — NOT (source, source) — so that
            # two different headless chunks from the same document don't
            # collide and silently drop one of them.
            quote = _truncate_quote(text)
            if quote:
                key = (source, f"{source}#{i}")
                if key not in best or score < best[key].score:
                    best[key] = Passage(source=source, ref=source, quote=quote, score=score)
    return sorted(best.values(), key=lambda p: p.score)[:k]


def search_quality_docs(query: str, k: int = 3) -> list[Passage]:
    if not query.strip():
        raise ValueError("empty query")
    backend = get_settings().docs_backend
    return _search_vertex(query, k) if backend == "vertex" else _search_local(query, k)
