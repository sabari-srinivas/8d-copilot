# 8D Copilot

A quality-engineering agent for an SMT electronics plant (Sree Electronics (fictional), Chennai):
a defect photo plus a customer complaint go in, and statistically tested root causes plus a
cited 8D report come out. This is a hackathon prototype; all plant, customer and defect data
is synthetic. This README is a stub — the full project documentation lands in a later task.

## Layout

```
prototype/
├── backend/            # Python: FastAPI app, agents, tools, synthetic data
│   ├── agent/
│   │   ├── agents/
│   │   ├── prompts/
│   │   ├── tools/
│   │   ├── tests/
│   │   │   └── fixtures/
│   │   ├── config.py
│   │   └── models.py
│   ├── data/
│   │   ├── docs/
│   │   ├── images/
│   │   └── out/
│   ├── infra/
│   │   ├── probe_models.py
│   │   ├── build_rag.py
│   │   └── load_data.sh
│   ├── pyproject.toml
│   └── pytest.ini
├── frontend/           # React UI (not yet created)
├── docs/
│   └── contract/       # API contract and mock JSON shared by backend and UI
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Fixtures

`backend/agent/tests/fixtures/vision_solder_bridge.json` and `vision_clean_board.json` are
**recorded real Gemini output**, not hand-written examples — produced by calling
`agent.tools.vision_tool.analyze_defect_image` against `data/images/defect_03.jpg` (the
golden-path solder-bridge image) and `data/images/no_defect_01.jpg` (the clean-board
image) respectively, and saving the typed `Defect` response. Both fixtures now genuinely
contain what their filenames say — see `data/images/IMAGES.md` for how that was arrived
at and how stable each read is. They let `agent/tests/test_vision_tool.py` test the wiring
(vision tool → Pydantic `Defect`) without ever calling the live model. Regenerate them
with:

```bash
python - <<'PY'
import pathlib
from agent.tools.vision_tool import analyze_defect_image
fx = pathlib.Path("agent/tests/fixtures")
for src, name in [("data/images/defect_03.jpg", "vision_solder_bridge.json"),
                  ("data/images/no_defect_01.jpg", "vision_clean_board.json")]:
    d = analyze_defect_image(pathlib.Path(src).read_bytes(), "image/jpeg")
    (fx / name).write_text(d.model_dump_json(indent=2) + "\n")
PY
```

whenever `agent/prompts/vision.md` changes — then check the regenerated `type` still
matches the filename before committing, since neither read is perfectly stable (see
Known issues).

## Quality-document search (RAG)

`agent.tools.doc_search.search_quality_docs()` has two backends behind `DOCS_BACKEND`
(default `local`): a local embedding search over `backend/data/docs/*.md` (embeds with
`EMBED_MODEL` through Vertex, so it alone satisfies "must use Google AI models"), and a
Vertex AI RAG Engine corpus built by `backend/infra/build_rag.py`. Both return the same
`Passage` shape, so the evidence agent never knows which one ran.

**RAG API used: `agentplatform`, not `vertexai.rag`.** The installed SDK
(`google-cloud-aiplatform`) marks `vertexai.rag` deprecated — importing it emits
`UserWarning: The vertexai.rag module is deprecated ... migrate to the agentplatform
client`. That replacement ships in the same package install (no extra dependency) and is
a genuine drop-in: `agentplatform.init is vertexai.init` — literally the same
`google.cloud.aiplatform.init` function object — and `agentplatform.rag` exposes the
identical call shape (`create_corpus`, `import_files`, `retrieval_query`, `list_corpora`,
`list_files`, `RagResource`, `RagVectorDbConfig`, `RagEmbeddingModelConfig`,
`VertexPredictionEndpoint`, `TransformationConfig`, `ChunkingConfig`,
`RagRetrievalConfig`), with no deprecation warning on import. So `build_rag.py` and
`doc_search._search_vertex` import `from agentplatform import rag` instead. Both are
confined to the vertex code path / infra script only — never imported at module load
time, so the test suite (run with `-W error::Warning`) never touches it.

**Region:** the corpus lives in `asia-south1`, same as the rest of the project's Vertex
resources (`GCP_REGION` / `VERTEX_REGION`). Source documents are staged at
`gs://<GCS_BUCKET>/docs/*.md` (bucket created idempotently by `build_rag.py` itself, in
the same region).

**Known asymmetry:** `Passage.score` is not comparable across backends. The local
backend reports cosine similarity (higher is more relevant). The Vertex RAG Engine's
native `score` is a distance (lower is more relevant) — confirmed empirically by
requesting progressively larger `top_k` against the live corpus and observing the same
leading contexts come back with monotonically increasing scores. `doc_search.py` sorts
each backend by its own correct direction; it does not rescale one into the other's
units.

Run `python -m infra.build_rag` once per project to build the corpus — it uploads
`data/docs/*.md` to GCS, creates (or reuses) the `quality-docs` corpus, imports the
files, writes `RAG_CORPUS=...` into `.env`, and proves the corpus answers (PRD Phase 2
gate: a test query returns PFMEA Row 14 with its source). All three steps
(bucket, corpus, file import) are idempotent — safe to re-run.

## Cloud backends

The app runs identically against local files (`PLANT_BACKEND=csv`, `STATE_BACKEND=memory`,
`DOCS_BACKEND=local`, `FILES_BACKEND=local`) or Google Cloud
(`PLANT_BACKEND=bigquery`, `STATE_BACKEND=firestore`, `DOCS_BACKEND=vertex`,
`FILES_BACKEND=gcs`) — `GET /api/health`'s `backends` object reports which. `.env.example`
commits the local values so a fresh clone works offline; the cloud values belong only in
the deployed `.env`, never in the repo.

`infra/load_data.sh` loads `lots`/`process`/`maintenance`/`complaints` into BigQuery
(idempotent — re-running overwrites rather than duplicating). The verification query
(average reflow peak temperature by line) should show Line 2 visibly higher than Line 1,
since every planted drift lot (`data/constants.DRIFT_LOT_IDS`) is on Line 2.

**Threading convention when a selector flips to its cloud form.** `agent/agents/__init__.py`
documents, call site by call site, which plant/state/files calls run through
`asyncio.to_thread` and why: under the local backends they are millisecond file I/O, but
under `PLANT_BACKEND=bigquery` / `STATE_BACKEND=firestore` / `FILES_BACKEND=gcs` the exact
same call sites become real network I/O, made from `async def` agent code on the single
asyncio event loop that also serves the SSE stream and `GET /api/health` (task 10's fix
protects this same loop from the model calls). A future call into a `*_BACKEND`-selected
tool from async code must follow the same convention — see the task 14 report
(`.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-14-report.md`) for the measured
before/after latency per selector.

**Cross-backend data-shape note.** `bigquery.QueryJob.to_dataframe()` returns a DATE
column as `datetime.date` objects (dtype `dbdate`), not a plain string the way
`pd.read_csv` does. `agent/tools/plant_data.py`'s `BigQueryPlantStore` normalises every
date-like column back to an ISO string immediately after reading, so every caller —
including `get_maintenance_events`'s raw record, which lands verbatim in an `Event.data`
dict seen by both the SSE stream's `json.dumps` and `FirestoreStateStore`'s Firestore
encoder — sees the same shape regardless of which `PlantStore` is behind `get_store()`.

## Known issues

- **`defect_03.jpg` is the golden-path solder-bridge image for the demo** (not
  `defect_01.jpg`, which earlier drafts of this README assumed). Under the final
  `agent/prompts/vision.md`, `defect_03.jpg` reads as `solder_bridge` (critical) in 2 of 3
  live calls and `none` in the third; `no_defect_01.jpg` reads as `none` in 3 of 4 calls
  and `misalignment` in the fourth. Both are majority-stable, not unanimous — re-run before
  a live demo if either image is called live rather than only through the recorded
  fixtures.
- **`defect_01.jpg` and `defect_02.jpg` are false negatives.** Both carry genuine,
  documented anomalies (see `data/images/IMAGES.md`) but both consistently read as `none`
  under the final prompt, across two independent rounds of prompt tightening. This was a
  deliberate trade-off: an earlier, blunter "uncertainty resolves toward none" rule made
  the clean-board image reliable but suppressed these two real defects as well; the
  current prompt distinguishes "unsure of type" from "no anomaly at all" and recovered
  `defect_04.jpg` and (mostly) `defect_03.jpg`, but not these two. Do not keep tuning the
  prompt against this without a plan — see
  `.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-5-report.md` for the full
  before/after table across both prompt revisions and all five images.
- `pip install -e ".[dev]"` from `backend/` succeeded on Python 3.12.15, including
  `google-adk>=1.0` (resolved to 1.14.1).
- **The Vertex RAG Engine backend's per-heading citation ranking is weaker than the
  local backend's.** The corpus's default chunking (`chunk_size=512, chunk_overlap=64`)
  routinely spans two full PFMEA rows per chunk; since the RAG Engine scores one chunk,
  not one heading, a highly relevant heading sharing a chunk with an irrelevant neighbour
  can lose a tie-break at a tight `k` cutoff. This does not affect the Phase 2 gate
  (which checks the raw top-3 chunks, not per-heading ranking) but means
  `search_quality_docs(..., k=3)` on `DOCS_BACKEND=vertex` does not reliably surface
  PFMEA Row 14 / Control plan Item 6 the way the local backend does. `DOCS_BACKEND=local`
  is the product default and does not have this weakness; see
  `.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-6-report.md` for the measured
  rankings on both backends.
