# 8D Copilot Prototype — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working 8D Copilot prototype that runs locally against real Google Cloud services — defect photo + complaint in, statistically tested root cause and cited 8D out, human-approved actions and quality memory at the end.

**Architecture:** A FastAPI backend hosts Google ADK agents (intake → vision → investigator → evidence → writer → actions) that stream progress to a React SPA over SSE. Every data source sits behind a small protocol with two backends — a local CSV/file backend used by tests and as a demo fallback, and a Google Cloud backend (BigQuery, Firestore, Cloud Storage, Vertex AI RAG Engine) selected by environment variable. The LLM only proposes hypotheses; a deterministic scipy module decides every verdict.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Google ADK, `google-genai` (Vertex AI mode), Pydantic v2, pandas, scipy, matplotlib, openpyxl · React 18 + Vite + TypeScript + Tailwind + Chart.js + react-router · BigQuery, Firestore (Native), Cloud Storage, Vertex AI RAG Engine · pytest.

**Source spec:** `../../../prototype /8D_Copilot_PRD.md` (identical copy at repo root `8D_Copilot_PRD.md`). Section references below (§N) point into it.

**Repo location:** `/Users/a2862717/Documents/AI Builder Cup/prototype/` — a fresh `git init` repo there, holding `backend/`, `frontend/` and `docs/`. The folder was renamed from `prototype ` (it had a trailing space, which breaks shell quoting and would have become the git root path). `8D_Copilot_PRD.md` already sits there and is read-only input.

---

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the PRD.

- **Golden rule (§9.1):** The LLM **proposes**. Deterministic Python **decides**. A human **approves**. The LLM never writes p-values, measurements or verdicts; the writer may only use numbers present in tool results.
- **Model names (§9.6):** Model name only from `GEMINI_MODEL` env var; embedding model from `EMBED_MODEL`. Never hard-code a model ID anywhere, including tests, comments and docs.
- **Verdict rule (§9.3, MUST):** `supported` only if p < 0.01 **and** the effect is in the hypothesised direction **and** the effect is meaningful (e.g. ≥ 3 °C for temperature). `rejected` if p > 0.1 **or** the effect is in the opposite direction. Otherwise `inconclusive`.
- **No hypothesis without a measurable parameter or event (§9.6).**
- **No number in the 8D that is not in a tool result (§9.6)** — enforced by a post-validation pass.
- **Structured output (§9.5):** Every LLM call that feeds code uses JSON schema / structured output and is validated with Pydantic. On validation failure: one retry, then an `error` event.
- **Never "operator error" as a root cause (§9.4).**
- **Responsive (§13, MUST):** works at 390 px and 1280 px, no horizontal scroll, camera upload on mobile, touch targets ≥ 44 px.
- **Accessibility (§13):** visible focus, alt text, verdict pills carry text (not colour only), respects reduced motion.
- **Latency (§13):** first visible result (defect box) < 10 s; full golden path < 90 s.
- **Honesty (§13):** footer on every screen reads `Synthetic demo data · Built with Gemini on Google Cloud`. Dataset credits in README (VisA CC BY 4.0).
- **Security (§13, §9.6):** no secrets in repo or logs; no image bytes or secrets in logs; Firestore written only by the API.
- **Branding (§14):** plant `Sree Electronics (fictional), Chennai`; customer `Hoshino Denso (fictional)`; second customer `Kaveri Motors (fictional)`; user chip `Priya R. · Quality Engineer`. No real company logos, no Google logos.
- **Region (§11.1):** `asia-south1` for data/storage/Firestore; model and RAG calls in whichever region the chosen model and RAG Engine support — record the choice in README.
- **Commits:** every task ends with a commit. Conventional-commit prefixes (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).

### Backend selector environment variables

Added beyond PRD §11.2 so the build is never blocked on cloud provisioning. Each defaults to the local value; the cloud value is the demo default once Task 2 lands.

| Variable | Values | Meaning |
|---|---|---|
| `PLANT_BACKEND` | `csv` \| `bigquery` | Where `lots`/`process`/`maintenance`/`complaints` come from |
| `STATE_BACKEND` | `memory` \| `firestore` | Where investigations, CAPA, holds, work orders, memory live |
| `DOCS_BACKEND` | `local` \| `vertex` | Quality-document search |
| `FILES_BACKEND` | `local` \| `gcs` | Images and chart PNGs |
| `REPLAY_CASE` | unset \| case name | Serves a recorded run instead of calling models (§13 reliability) |

---

## File Structure

```
prototype/                   <- git repo root
  CLAUDE.md                  golden rule, contract rule, model-from-env rule
  README.md  .env.example  .gitignore  firebase.json
  8D_Copilot_PRD.md          the spec (already here, read-only input)

  backend/                   everything Python. All backend commands run from HERE.
    pyproject.toml  pytest.ini  Dockerfile  .dockerignore
    agent/
      main.py                FastAPI app: 7 endpoints + SSE + static chart serving
      config.py              Settings (pydantic-settings), one per-process singleton
      models.py              every Pydantic model crossing a boundary
      events.py              Event model, EventBus (history + live fan-out), SSE framing
      state.py               StateStore protocol, MemoryStateStore, FirestoreStateStore
      orchestrator.py        runs the agent pipeline for one investigation
      replay.py              record/replay a run when the network is unreliable
      agents/   intake.py vision.py investigator.py evidence.py writer.py actions.py
      tools/    plant_data.py stats_test.py stats_verdict.py charts.py vision_tool.py
                doc_search.py memory.py intake_tools.py storage.py provenance.py llm.py
      prompts/  intake.md vision.md investigator.md writer.md customer_reply.md
      tests/    one test module per tool + test_api_contract.py
                fixtures/ (recorded model responses, sample xlsx, sample image)
    data/
      constants.py           thresholds, lot windows, min-effect table — single source of truth
      generate_plant.py  check_plant.py  make_docs.py
      docs/                  pfmea.md control_plan.md past_8d_tombstoning.md past_8d_voids.md
      images/                demo photos + IMAGES.md (source + licence per file)
      out/                   generated CSVs, xlsx, charts  (gitignored except .gitkeep)
    infra/
      probe_models.py  load_data.sh  build_rag.py  run_cases.py

  frontend/                  everything React. All frontend commands run from HERE.
    package.json  vite.config.ts  tailwind.config.js  index.html
    src/api/        client.ts types.ts useInvestigationStream.ts mocks.ts
    src/components/ AppShell.tsx VerdictPill.tsx HypothesisCard.tsx Timeline.tsx
                    DefectPhoto.tsx CitationChip.tsx CitationSheet.tsx EightDSection.tsx
                    ActionToggle.tsx TempChart.tsx
    src/pages/      Inbox.tsx NewInvestigation.tsx LiveInvestigation.tsx Evidence.tsx
                    Review.tsx Done.tsx Memory.tsx

  docs/
    contract/   README.md  mock_events.json  mock_investigation.json
    plans/      this plan
```

**Why this split:** `backend/` and `frontend/` are the two deliverables, each with its own toolchain, its own dependency file and its own working directory — a subagent working on one never needs to reason about the other. `docs/contract/` sits above both because it is the agreement *between* them; neither owns it, and a change there needs both sides.

Inside the backend, files that change together live together. `data/constants.py` is imported by both the generator and the statistics tool, so the planted-truth thresholds can never drift apart. Each tool file owns one protocol plus its two backends, so swapping CSV → BigQuery touches one file. Agents are one file each because their prompts and output schemas change independently.

### Working directories — read this before any command

| Doing | `cd` to | Why |
|---|---|---|
| Any `python`, `pytest`, `uvicorn`, `pip` | `prototype/backend` | `agent`, `data` and `infra` are top-level packages there, so `import agent.models` and `python -m data.check_plant` resolve |
| Any `npm`, `vite` | `prototype/frontend` | |
| `git`, `firebase deploy`, `gh` | `prototype` | repo root |

Python module paths (`agent.config`, `data.constants`) are unchanged by the split — they are relative to `backend/`, which is on `sys.path` once `pip install -e .` has run there.

**Two cross-folder paths need care** (both are called out in the tasks that create them):
1. `backend/agent/tests/test_api_contract.py` reads the mock JSON from `docs/contract/`, which is now one level further up: `Path(__file__).resolve().parents[3] / "docs" / "contract"` (tests → agent → backend → **prototype**).
2. `frontend/src/api/useInvestigationStream.ts` imports `mock_events.json` from outside the Vite root. Add to `frontend/vite.config.ts`:

```ts
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@contract": path.resolve(__dirname, "../docs/contract") } },
  server: { fs: { allow: [path.resolve(__dirname, ".."), __dirname] } },
});
```

then import as `@contract/mock_events.json`.

---

## Task Order and Cut Lines

Tasks 0–12 produce the locally running prototype the PRD calls today's goal. Tasks 13–14 are the weekend deployment and submission assets.

**If time runs short, cut in this order (and say so in the README):** Task 11 replay mode → the `/memory` page (fold into the inbox, §7) → the second customer complaint card → Vertex RAG backend (keep `DOCS_BACKEND=local`, which still uses Gemini embeddings) → BigQuery backend (keep `PLANT_BACKEND=csv`). Never cut: the direction-aware verdict rule, the visible rejected hypotheses, the synthetic-data labels, or the human approval gate — those are the answers to §17's judge questions.

---

### Task 0: Toolchain, repo skeleton, contract and mocks

**Files:**
- Create: `prototype/.gitignore`, `prototype/backend/pyproject.toml`, `prototype/backend/pytest.ini`, `prototype/CLAUDE.md`, `prototype/.env.example`, `prototype/README.md`
- Create: `prototype/backend/agent/config.py`, `prototype/backend/agent/models.py`, `prototype/backend/agent/__init__.py`, `prototype/backend/agent/tests/__init__.py`, `prototype/backend/agent/tests/conftest.py`, `prototype/backend/agent/tests/test_models.py`
- Create: `prototype/docs/contract/README.md`, `prototype/docs/contract/mock_events.json`, `prototype/docs/contract/mock_investigation.json`
- Create: `prototype/backend/infra/probe_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `agent.config.settings` (a `Settings` instance with every env var as a typed attribute); every Pydantic model used across tasks — `Complaint`, `Defect`, `Hypothesis`, `HypothesisResult`, `Citation`, `EightDSection`, `EightD`, `ProposedAction`, `Investigation`, `MemoryEntry`, `TravelerRow`, `Passage`, `Event`. `docs/contract/mock_events.json` and `mock_investigation.json` are the UI's build target in Tasks 9–10.

- [ ] **Step 1: Install the missing toolchain**

The probe found Python 3.11 and 3.14 but no 3.12, and no `gcloud` or `firebase`. Google ADK and the Google Cloud client libraries are not yet built for 3.14.

```bash
brew install python@3.12
brew install --cask google-cloud-sdk
npm install -g firebase-tools
python3.12 --version   # expect Python 3.12.x
gcloud --version | head -1
firebase --version
```

- [ ] **Step 2: Create the repo and virtual environment**

```bash
cd "/Users/a2862717/Documents/AI Builder Cup/prototype"
git init -b main
mkdir -p backend/agent/tools backend/agent/agents backend/agent/prompts \
         backend/agent/tests/fixtures backend/data/docs backend/data/images \
         backend/data/out backend/infra docs/contract
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

- [ ] **Step 3: Write `prototype/.gitignore`**

Written at the repo root, `prototype/.gitignore`:

```
backend/.venv/
__pycache__/
*.pyc
.env
.env.local
.env.production
backend/data/out/*
!backend/data/out/.gitkeep
frontend/node_modules/
frontend/dist/
.DS_Store
.pytest_cache/
```

```bash
touch backend/data/out/.gitkeep
```

- [ ] **Step 4: Write `backend/pyproject.toml`**

```toml
[project]
name = "8d-copilot"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "python-multipart>=0.0.12",
  "google-adk>=1.0",
  "google-genai>=1.0",
  "google-cloud-bigquery>=3.26",
  "google-cloud-firestore>=2.19",
  "google-cloud-storage>=2.18",
  "pandas>=2.2",
  "numpy>=2.0",
  "scipy>=1.14",
  "matplotlib>=3.9",
  "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.27"]

[tool.setuptools.packages.find]
include = ["agent*", "data*", "infra*"]
```

```bash
pip install -e ".[dev]"
```

If `google-adk` fails to resolve on 3.12, record the error in `README.md` under "Known issues" and continue — Task 7 has an explicit fallback that keeps the same agent boundaries.

- [ ] **Step 5: Write `backend/pytest.ini`**

```ini
[pytest]
testpaths = agent/tests
asyncio_mode = auto
filterwarnings = ignore::DeprecationWarning
```

- [ ] **Step 6: Write `prototype/.env.example`**

At the repo root, shared by both folders. Exactly the PRD §11.2 list plus the backend selectors. No real values. `backend/agent/config.py` reads `../.env`; `frontend/` reads its own `.env.local` for the two `VITE_*` values.

```bash
# --- Google Cloud (PRD 11.2) ---
GCP_PROJECT=
GCP_REGION=asia-south1
VERTEX_REGION=
GEMINI_MODEL=
EMBED_MODEL=
BQ_DATASET=plant
GCS_BUCKET=
RAG_CORPUS=
FIRESTORE_DB=(default)
DEMO_ACCESS_CODE=

# --- Frontend ---
VITE_API_URL=http://localhost:8000
VITE_USE_MOCKS=true

# --- Backend selectors (local-first defaults) ---
PLANT_BACKEND=csv
STATE_BACKEND=memory
DOCS_BACKEND=local
FILES_BACKEND=local
REPLAY_CASE=
```

- [ ] **Step 7: Write `prototype/CLAUDE.md`**

```markdown
# 8D Copilot — rules for code in this repo

1. **Golden rule.** The LLM proposes. Deterministic Python decides. A human approves.
   The LLM never writes a p-value, a measurement or a verdict. `agent/tools/stats_test.py`
   is the only module allowed to produce a verdict.
2. **Contract rule.** `docs/contract/README.md` is the agreement between backend and UI.
   If you need to change a field name, a status value or an event type, stop and say so —
   both sides must change together.
3. **Model names come only from env.** `GEMINI_MODEL` and `EMBED_MODEL`. Never hard-code a
   model ID in code, tests, comments or docs.
4. **No number in the 8D that is not in a tool result.** `agent/tools/provenance.py` checks this.
5. **All demo data is synthetic** and is labelled as synthetic in the UI, README and deck.
6. **No secrets, no image bytes in logs.**
7. Small files, one responsibility each. A test for every tool.
```

- [ ] **Step 8: Write `agent/config.py`**

```python
"""Typed settings. Every value comes from the environment — never a literal model ID."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives at the repo root (prototype/), one level above backend/.
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env"), extra="ignore")

    gcp_project: str = ""
    gcp_region: str = "asia-south1"
    vertex_region: str = ""
    gemini_model: str = ""
    embed_model: str = ""
    bq_dataset: str = "plant"
    gcs_bucket: str = ""
    rag_corpus: str = ""
    firestore_db: str = "(default)"
    demo_access_code: str = ""

    plant_backend: str = "csv"
    state_backend: str = "memory"
    docs_backend: str = "local"
    files_backend: str = "local"
    replay_case: str = ""

    def require_model(self) -> str:
        if not self.gemini_model:
            raise RuntimeError("GEMINI_MODEL is not set. Models are never hard-coded.")
        return self.gemini_model

    def require_embed_model(self) -> str:
        if not self.embed_model:
            raise RuntimeError("EMBED_MODEL is not set. Models are never hard-coded.")
        return self.embed_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 9: Write the failing test for the models and settings**

`agent/tests/test_models.py`:

```python
import pytest
from agent.config import Settings
from agent.models import Defect, Hypothesis, HypothesisResult, EightD, Investigation


def test_model_name_must_come_from_env():
    s = Settings(gemini_model="")
    with pytest.raises(RuntimeError, match="never hard-coded"):
        s.require_model()


def test_defect_box_is_four_fractions():
    d = Defect(type="solder_bridge", severity="major", box=[0.1, 0.2, 0.3, 0.1],
               confidence=0.86, visual_evidence="Bright metal bridge between two fine-pitch pads.")
    assert len(d.box) == 4
    assert all(0.0 <= v <= 1.0 for v in d.box)


def test_defect_rejects_unknown_type():
    with pytest.raises(ValueError):
        Defect(type="banana", severity="major", box=[0, 0, 1, 1],
               confidence=0.5, visual_evidence="x")


def test_hypothesis_requires_a_parameter_or_an_event():
    with pytest.raises(ValueError, match="parameter or event"):
        Hypothesis(id="H9", category="Method", text="Something vague", direction="higher")


def test_investigation_statuses_are_the_contract_values():
    assert set(Investigation.model_fields["status"].annotation.__args__) == {
        "running", "draft_ready", "approved", "insufficient_evidence"}


def test_eight_d_has_all_eight_sections():
    assert [f for f in EightD.model_fields] == [f"D{i}" for i in range(1, 9)]


def test_hypothesis_result_verdicts_are_the_contract_values():
    assert set(HypothesisResult.model_fields["verdict"].annotation.__args__) == {
        "supported", "rejected", "inconclusive"}
```

- [ ] **Step 10: Run the test to verify it fails**

Run: `pytest agent/tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.models'`

- [ ] **Step 11: Write `agent/models.py`**

```python
"""Every model that crosses a boundary. Field names here ARE the API contract."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator

DefectType = Literal["solder_bridge", "missing_component", "misalignment",
                     "scratch", "contamination", "other", "none"]
Severity = Literal["critical", "major", "minor", "none"]
Verdict = Literal["supported", "rejected", "inconclusive"]
Direction = Literal["higher", "lower", "any"]
SixM = Literal["Machine", "Method", "Material", "Man", "Measurement", "Environment"]
Status = Literal["running", "draft_ready", "approved", "insufficient_evidence"]
ActionKind = Literal["capa", "hold", "work_order", "customer_reply"]


class Complaint(BaseModel):
    complaint_id: str
    customer: str
    product: str
    lot_id: str
    defect: str
    qty_affected: int | None = None
    qty_shipped: int | None = None
    received: str = ""
    eight_d_due: str = ""
    status: Literal["open", "closed"] = "open"
    text: str = ""
    due_in_working_days: int | None = None


class Defect(BaseModel):
    type: DefectType
    severity: Severity
    box: list[float] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    visual_evidence: str

    @model_validator(mode="after")
    def _box_in_unit_square(self):
        if any(v < 0.0 or v > 1.0 for v in self.box):
            raise ValueError("box values must be 0-1 fractions")
        return self


class Hypothesis(BaseModel):
    """Proposed by the LLM. Carries NO verdict and NO numbers — those come from the stats tool."""
    id: str
    category: SixM
    text: str
    parameter: str | None = None
    event_wo_id: str | None = None
    direction: Direction = "any"

    @model_validator(mode="after")
    def _needs_something_measurable(self):
        if not self.parameter and not self.event_wo_id:
            raise ValueError("a hypothesis needs one measurable parameter or event")
        return self


class HypothesisResult(BaseModel):
    """Produced ONLY by agent/tools/stats_test.py."""
    hypothesis_id: str
    verdict: Verdict
    test: str
    p_value: float
    effect: str
    effect_value: float
    effect_unit: str
    n_defect: int
    n_good: int
    group_labels: list[str] = Field(default_factory=list)
    chart_url: str | None = None


class Citation(BaseModel):
    label: str
    source: str
    ref: str
    quote: str = ""


class EightDSection(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)


class EightD(BaseModel):
    D1: EightDSection
    D2: EightDSection
    D3: EightDSection
    D4: EightDSection
    D5: EightDSection
    D6: EightDSection
    D7: EightDSection
    D8: EightDSection


class ProposedAction(BaseModel):
    id: str
    kind: ActionKind
    summary: str
    payload: dict = Field(default_factory=dict)


class MemoryEntry(BaseModel):
    id: str
    defect_type: str
    root_cause: str
    parameter: str = ""
    line: str = ""
    capa_id: str = ""
    lot_id: str = ""
    created: str = ""


class TravelerRow(BaseModel):
    lot_id: str
    date: str = ""
    shift: str = ""
    operator_id: str = ""
    reflow_peak_temp_c: float | None = None
    time_above_liquidus_s: float | None = None
    aoi_bridges: int | None = None
    remarks: str = ""
    low_confidence_fields: list[str] = Field(default_factory=list)


class Passage(BaseModel):
    source: str
    ref: str
    quote: str
    score: float = 0.0


class Investigation(BaseModel):
    id: str
    status: Status = "running"
    complaint_id: str = ""
    lot_id: str = ""
    created: str = ""
    photo_url: str = ""
    defect: Defect | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    results: list[HypothesisResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    traveler_rows: list[TravelerRow] = Field(default_factory=list)
    eight_d: EightD | None = None
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    memory_hits: list[MemoryEntry] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    approver: str = ""
    chart_url: str | None = None
```

- [ ] **Step 12: Run the tests to verify they pass**

Run: `pytest agent/tests/test_models.py -v`
Expected: 7 passed

- [ ] **Step 13: Write `docs/contract/README.md`** (at `prototype/docs/contract/`, not inside either code folder)

Transcribe PRD §12 exactly — all seven endpoints, the SSE event envelope with the `memory_hit` and `insufficient_evidence` additions, and the `hypothesis_result.data` shape. Open the file with this note so the drift from the Team Playbook's older four-endpoint contract is explicit:

```markdown
# 8D Copilot API contract

Authoritative. Supersedes the four-endpoint sketch in `8D_Copilot_Team_Playbook.md` §4.
Any change needs both the backend and UI owner to approve the pull request.

Base: `{API_URL}/api`
```

Then the seven endpoints from PRD §12 verbatim, and this table of event types so the UI can switch on them exhaustively:

| `type` | emitted by | `data` |
|---|---|---|
| `step_started` | any | `{}` |
| `tool_call` | any | `{"tool": "...", "args": {...}}` |
| `tool_result` | any | `{"tool": "...", "summary": "..."}` |
| `memory_hit` | investigator | `MemoryEntry` |
| `hypothesis` | investigator | `Hypothesis` |
| `hypothesis_result` | investigator | `HypothesisResult` |
| `citation` | evidence | `Citation` |
| `draft_ready` | writer | `{"status": "draft_ready" \| "insufficient_evidence"}` |
| `done` | system | `{}` |
| `error` | system | `{"message": "..."}` |

- [ ] **Step 14: Write `docs/contract/mock_events.json`**

17 events replaying the §8 golden path, in this order. Write real values — the UI is built against these before any model call exists.

1. `system / step_started` — "Investigation started"
2. `intake / tool_call` — "Reading complaint C-2026-031"
3. `intake / tool_result` — "Hoshino Denso (fictional) · ECU-PCB-7 · lot L2611 · 14 of 500"
4. `intake / tool_result` — "Read 9 rows from lot_traveler_line2_wk41.xlsx"
5. `vision / step_started` — "Looking at the defect photo"
6. `vision / tool_result` — data: `{"type":"solder_bridge","severity":"major","box":[0.41,0.36,0.17,0.12],"confidence":0.86,"visual_evidence":"Continuous bright solder joining two adjacent fine-pitch pads."}`
7. `investigator / step_started` — "Checking quality memory"
8. `investigator / tool_result` — "No similar past case found"
9. `investigator / hypothesis` — H1 Machine, stencil wear, parameter `stencil_print_count`, direction `higher`
10. `investigator / hypothesis_result` — H1 `rejected`, p 0.0001, effect `-38,400 prints (new stencil ST-07B)`, n 6/58
11. `investigator / hypothesis` — H2 Machine, reflow peak temperature drift after WO-388, parameter `reflow_peak_temp_c`, event `WO-388`, direction `higher`
12. `investigator / hypothesis_result` — H2 `supported`, p 0.0000, effect `+8.2 °C mean peak temp`, n 6/58, `chart_url` `/api/charts/mock_reflow.png`
13. `investigator / hypothesis` — H3 Environment, room humidity, parameter `room_humidity_pct`, direction `higher`
14. `investigator / hypothesis_result` — H3 `rejected`, p 0.62, effect `+0.4 %RH`, n 6/58
15. `investigator / hypothesis` — H4 Man, operator change OP-17, parameter `operator_id`, direction `higher`
16. `investigator / hypothesis_result` — H4 `inconclusive`, p 0.041, effect `+0.52 share of OP-17 lots`, test `Fisher exact`, n 6/58
17. `evidence / citation` ×2 (PFMEA row 14, Control plan item 6), then `writer / draft_ready` with `{"status":"draft_ready"}`, then `system / done`

Each event needs `seq`, `ts` (600 ms apart starting `2026-10-16T10:02:00Z`), `agent`, `type`, `title`, `detail`, `data`.

- [ ] **Step 15: Write `docs/contract/mock_investigation.json`**

A complete `Investigation` for `inv_mock`: status `draft_ready`, the defect from event 6, the four hypotheses and results from events 9–16, two citations, full D1–D8 text written the way the §9.4 writer prompt demands (every factual sentence ends with a bracketed citation; D3 names lots L2609–L2614; D4 states the cause, that it was verified by Welch t-test p < 0.01 with +8.2 °C effect, and that it escaped because WO-388's post-check was `profile_verification_pending`), and four `proposed_actions` A1–A4 (capa, hold, work_order, customer_reply).

- [ ] **Step 16: Write `infra/probe_models.py`**

PRD §11.1 says to confirm the model ID in Model Garden rather than trusting a written-down name.

```python
"""Prints the Gemini and embedding models available to this project/region.
Run after `gcloud auth application-default login`. Copy the IDs you pick into .env."""
import os
from google import genai

project = os.environ["GCP_PROJECT"]
region = os.environ.get("VERTEX_REGION") or os.environ["GCP_REGION"]
client = genai.Client(vertexai=True, project=project, location=region)

for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    print(f"{m.name:60} {','.join(actions)}")

print("\nPick a GA Gemini Flash model for GEMINI_MODEL and a text-embedding model "
      "for EMBED_MODEL. Record the region you used in README.md.")
```

- [ ] **Step 17: Commit**

```bash
git add -A
git commit -m "chore: repo skeleton, settings, models, API contract and mocks"
```

---

### Task 1: Planted-truth data that survives the direction-aware rule

The two scripts in `Claude outputs/` are the starting point. Three things must change: the defect window leaks past L2609–L2614, `check_plant.py` only prints where the PRD says it must assert, and its verdict rule ignores direction — which would mark the stencil decoy `supported` instead of `rejected`.

**Files:**
- Create: `prototype/backend/data/constants.py`
- Create: `prototype/backend/data/generate_plant.py` (seeded from `../Claude outputs/generate_plant.py`)
- Create: `prototype/backend/data/check_plant.py` (rewritten from `../Claude outputs/check_plant.py`)
- Create: `prototype/backend/agent/tests/test_verdict_rule.py`
- Create: `prototype/backend/agent/tools/stats_verdict.py`

**Interfaces:**
- Consumes: `agent.models.Verdict`.
- Produces: `data.constants` — `SEED`, `PRODUCT`, `DRIFT_LOT_IDS`, `WO388_ID`, `WO388_DATE`, `DEFECT_RATE_THRESHOLD`, `MIN_EFFECT`, `PARAM_UNITS`; `agent.tools.stats_verdict.classify(p_value, effect, direction, min_effect) -> Verdict`. Task 3's `test_hypothesis` calls `classify`; `check_plant.py` calls the same function so the data gate and the runtime agree by construction.

- [ ] **Step 1: Write `data/constants.py`**

```python
"""Single source of truth for the planted scenario. Imported by the generator,
the data gate and the statistics tool so their thresholds can never drift apart."""

SEED = 2611
PRODUCT = "ECU-PCB-7"
PLANT = "Sree Electronics (fictional), Chennai"

START_DATE = "2026-09-14"
END_DATE = "2026-10-13"
WO388_ID = "WO-388"
WO388_DATE = "2026-10-08"      # reflow oven zone 7 heater replaced, profile verification pending
WO386_DATE = "2026-10-07"      # new stencil ST-07B installed on Line 2
OP17_START = "2026-10-06"

LOT_NUM_RANGE = (2551, 2615)                                   # 64 lots
DRIFT_LOT_IDS = [f"L{n}" for n in range(2609, 2615)]           # L2609-L2614, all Line 2
GOLDEN_LOT = "L2611"
GOLDEN_BRIDGES = 14                                            # matches complaint C-2026-031

DEFECT_RATE_THRESHOLD = 0.012      # a lot is a "defect lot" above this solder-bridge rate

# PRD 9.3: an effect must be meaningful, not merely significant.
MIN_EFFECT = {
    "reflow_peak_temp_c": 3.0,
    "time_above_liquidus_s": 5.0,
    "preheat_ramp_c_per_s": 0.3,
    "soak_time_s": 10.0,
    "conveyor_speed_cm_min": 3.0,
    "paste_age_h": 4.0,
    "room_humidity_pct": 5.0,
    "stencil_print_count": 5000.0,
    "squeegee_pressure_kg": 0.5,
    "operator_id": 0.15,           # difference in share of lots, 0-1
}

PARAM_UNITS = {
    "reflow_peak_temp_c": "°C",
    "time_above_liquidus_s": "s",
    "preheat_ramp_c_per_s": "°C/s",
    "soak_time_s": "s",
    "conveyor_speed_cm_min": "cm/min",
    "paste_age_h": "h",
    "room_humidity_pct": "%RH",
    "stencil_print_count": "prints",
    "squeegee_pressure_kg": "kg",
    "operator_id": "share of lots",
}

REFLOW_PEAK_LIMIT_C = 250.0        # profile limit drawn on the evidence chart
```

- [ ] **Step 2: Write the failing test for the verdict rule**

`agent/tests/test_verdict_rule.py` — these cases encode PRD §9.3 and the five required verdicts of §10.3.

```python
import pytest
from data.constants import MIN_EFFECT
from agent.tools.stats_verdict import classify


def test_supported_needs_significance_direction_and_size():
    assert classify(p_value=0.0001, effect=+8.2, direction="higher",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "supported"


def test_opposite_direction_is_rejected_however_significant():
    """H1 stencil wear: a NEW stencil means the defect lots have FEWER prints.
    A p-only rule would call this supported. The direction rule rejects it."""
    assert classify(p_value=1e-9, effect=-38400.0, direction="higher",
                    min_effect=MIN_EFFECT["stencil_print_count"]) == "rejected"


def test_lower_direction_rejects_a_positive_effect():
    assert classify(p_value=1e-9, effect=+5.0, direction="lower", min_effect=1.0) == "rejected"


def test_high_p_value_is_rejected():
    assert classify(p_value=0.62, effect=+0.4, direction="higher",
                    min_effect=MIN_EFFECT["room_humidity_pct"]) == "rejected"


def test_middle_p_value_is_inconclusive():
    assert classify(p_value=0.041, effect=+0.52, direction="higher",
                    min_effect=MIN_EFFECT["operator_id"]) == "inconclusive"


def test_significant_but_trivial_effect_is_inconclusive():
    assert classify(p_value=0.0001, effect=+1.1, direction="higher",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "inconclusive"


def test_direction_any_ignores_sign():
    assert classify(p_value=0.0001, effect=-8.2, direction="any",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "supported"


@pytest.mark.parametrize("p", [0.01, 0.1])
def test_boundaries_are_not_supported(p):
    assert classify(p_value=p, effect=+8.2, direction="higher", min_effect=3.0) != "supported"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest agent/tests/test_verdict_rule.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.tools.stats_verdict'`

- [ ] **Step 4: Write `agent/tools/stats_verdict.py`**

```python
"""The verdict rule. PRD 9.3, direction-aware. No LLM inside, no numbers invented.

supported    p < 0.01 AND effect in the hypothesised direction AND |effect| >= min_effect
rejected     p > 0.1  OR  effect in the opposite direction
inconclusive otherwise
"""
from agent.models import Direction, Verdict

P_SUPPORTED = 0.01
P_REJECTED = 0.10


def classify(p_value: float, effect: float, direction: Direction, min_effect: float) -> Verdict:
    if direction == "higher" and effect < 0:
        return "rejected"
    if direction == "lower" and effect > 0:
        return "rejected"
    if p_value > P_REJECTED:
        return "rejected"
    if p_value < P_SUPPORTED and abs(effect) >= min_effect:
        return "supported"
    return "inconclusive"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest agent/tests/test_verdict_rule.py -v`
Expected: 9 passed

- [ ] **Step 6: Port the generator and close the defect-window leak**

Copy `../Claude outputs/generate_plant.py` to `data/generate_plant.py`, then make these four changes.

**6a. Import the constants** instead of redefining `SEED`, `PRODUCT`, `WO388_DATE` and the drift lot list.

**6b. Fix the line assignment** so no Line 2 lot other than L2609–L2614 is dated after WO-388. In the original, `drift` is computed as `line == "L2" and date > WO388_DATE`, and lots L2606–L2608 can satisfy that by index parity — which would spread the defect window past the hold list the demo and the 8D depend on. Replace the line-assignment branch with:

```python
    lot_id = f"L{lot}"
    after_wo388 = d > pd.Timestamp(WO388_DATE)
    if lot_id in DRIFT_LOT_IDS:
        line = "L2"                      # Line 1 ran ECU-PCB-9 on these days
    elif after_wo388:
        line = "L1"                      # keep the post-WO-388 L2 window exactly the drift lots
    else:
        line = "L1" if i % 2 == 0 else "L2"
```

**6c. Keep the physical drift rule** (`line == "L2" and date > WO388_DATE`) in both the process loop and `bridges()` — the cause is physical, not a lookup — but add this invariant right after the frames are built, so the construction is proved rather than assumed:

```python
post = lots[(lots.line == "L2") & (pd.to_datetime(lots.date) > pd.Timestamp(WO388_DATE))]
assert sorted(post.lot_id) == sorted(DRIFT_LOT_IDS), (
    f"post-WO-388 Line 2 lots {sorted(post.lot_id)} != drift lots {sorted(DRIFT_LOT_IDS)}")
```

**6d. Add a `--seed` argument** so Step 8 can sweep for the H4 tuning without editing the file:

```python
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=SEED)
ap.add_argument("--op17-l1-share", type=float, default=0.15)
args = ap.parse_args()
rng = np.random.default_rng(args.seed)
```

and use `args.op17_l1_share` in the Line 1 operator draw: `p=[0.45, 0.55 - args.op17_l1_share, args.op17_l1_share]`.

- [ ] **Step 7: Write `data/check_plant.py` as an asserting gate**

PRD §10.3 and the Phase 1 gate both require assertions. This file is the Task 1 acceptance test.

```python
"""check_plant.py — the planted cause must be detectable and the decoys must not be.
Uses the SAME verdict rule the agent uses at runtime (agent/tools/stats_verdict.classify),
so the data gate and the product can never disagree.

Exit 0 = the dataset is demo-ready. Exit 1 = regenerate or retune.
"""
import sys
from pathlib import Path
import pandas as pd
from scipy import stats

from data.constants import (DEFECT_RATE_THRESHOLD, DRIFT_LOT_IDS, GOLDEN_BRIDGES,
                            GOLDEN_LOT, MIN_EFFECT, PARAM_UNITS, WO388_DATE)
from agent.tools.stats_verdict import classify

OUT = Path(__file__).parent / "out"
lots = pd.read_csv(OUT / "lots.csv")
df = lots.merge(pd.read_csv(OUT / "process.csv"), on="lot_id")
df["bridge_rate"] = df.defects_solder_bridge / df.qty
bad = df.bridge_rate > DEFECT_RATE_THRESHOLD

CASES = [
    # id,  description,                              column,                  direction, required
    ("H2", "Reflow peak temp drift (L2, WO-388)",    "reflow_peak_temp_c",    "higher", "supported"),
    ("H2b", "Time above liquidus",                   "time_above_liquidus_s", "higher", "supported"),
    ("H1", "Stencil wear (print count)",             "stencil_print_count",   "higher", "rejected"),
    ("H3", "Room humidity",                          "room_humidity_pct",     "higher", "rejected"),
    ("H5", "Paste age",                              "paste_age_h",           "higher", "rejected"),
]

failures: list[str] = []
print(f"defect lots ({int(bad.sum())}): {sorted(df[bad].lot_id)}\n")
print(f"{'id':5}{'hypothesis':40}{'test':10}{'p':>9}  {'effect':>14}  {'verdict':13}required")

for hid, name, col, direction, required in CASES:
    _, p = stats.ttest_ind(df[bad][col], df[~bad][col], equal_var=False)
    eff = float(df[bad][col].mean() - df[~bad][col].mean())
    got = classify(p, eff, direction, MIN_EFFECT[col])
    flag = "" if got == required else "   <-- FAIL"
    print(f"{hid:5}{name:40}{'Welch t':10}{p:9.4f}  {eff:+10.1f} {PARAM_UNITS[col]:<4} {got:13}{required}{flag}")
    if got != required:
        failures.append(f"{hid} ({name}): got {got}, required {required}, p={p:.4f}, effect={eff:+.1f}")

# H4 operator: share of OP-17 lots among defect vs good lots, Fisher exact.
tab = pd.crosstab(df.operator_id == "OP-17", bad)
_, p4 = stats.fisher_exact(tab.values)
share_bad = float((df[bad].operator_id == "OP-17").mean())
share_good = float((df[~bad].operator_id == "OP-17").mean())
eff4 = share_bad - share_good
got4 = classify(p4, eff4, "higher", MIN_EFFECT["operator_id"])
flag = "" if got4 == "inconclusive" else "   <-- FAIL"
print(f"{'H4':5}{'Operator change (OP-17)':40}{'Fisher':10}{p4:9.4f}  {eff4:+10.2f} {'share':<4} {got4:13}inconclusive{flag}")
if got4 != "inconclusive":
    failures.append(f"H4 operator: got {got4}, required inconclusive, p={p4:.4f}. "
                    f"Retune with --op17-l1-share until Fisher p lands in 0.01..0.1.")

# Structural invariants the demo and the 8D depend on.
checks = {
    "defect lots are exactly the drift lots":
        sorted(df[bad].lot_id) == sorted(DRIFT_LOT_IDS),
    f"{GOLDEN_LOT} has exactly {GOLDEN_BRIDGES} bridges (matches complaint C-2026-031)":
        int(df.loc[df.lot_id == GOLDEN_LOT, "defects_solder_bridge"].iloc[0]) == GOLDEN_BRIDGES,
    "no Line 2 lot after WO-388 outside the drift window":
        sorted(df[(df.line == "L2") & (pd.to_datetime(df.date) > pd.Timestamp(WO388_DATE))].lot_id)
        == sorted(DRIFT_LOT_IDS),
    "drift lots exceed the 250 C profile limit on average":
        float(df[df.lot_id.isin(DRIFT_LOT_IDS)].reflow_peak_temp_c.mean()) > 250.0,
}
print()
for name, ok in checks.items():
    print(f"[{'ok' if ok else 'FAIL'}] {name}")
    if not ok:
        failures.append(name)

if failures:
    print("\nFAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nAll required verdicts and invariants hold. Dataset is demo-ready.")
```

- [ ] **Step 8: Generate, run the gate, and tune H4 until it lands inconclusive**

```bash
python -m data.generate_plant
python -m data.check_plant
```

H4 is the one case that needs tuning: OP-17 runs most drift lots, so Fisher's p will likely start below 0.01 (`supported`, which fails). PRD §10.3 says to tune until it sits between 0.01 and 0.1. Raise OP-17's share of *good* Line 1 lots — this is the confounding the hypothesis is meant to show — and sweep:

```bash
for share in 0.15 0.25 0.35 0.45; do
  for seed in 2611 2612 2613 2614 2615; do
    python -m data.generate_plant --seed $seed --op17-l1-share $share >/dev/null
    if python -m data.check_plant >/dev/null 2>&1; then
      echo "PASS seed=$seed op17_l1_share=$share"; break 2
    fi
  done
done
```

Write the winning pair back into `data/constants.py` as `SEED` and add `OP17_L1_SHARE`, make them the argparse defaults, regenerate once, and confirm `python -m data.check_plant` exits 0 with every row matching its required verdict.

- [ ] **Step 9: Verify the messy Excel still reflects the regenerated data**

```bash
python - <<'PY'
import openpyxl
wb = openpyxl.load_workbook("data/out/lot_traveler_line2_wk41.xlsx")
ws = wb.active
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
    print(row)
PY
```

Expected, per PRD §10.4: two title rows above the header, short column names (`Lot#`, `Dt`, `Opr`, `Oven peak (C) [from printout]`), dates as `dd/mm`, the literal string `same as prev` in L2613's peak-temperature cell, and the free-text remarks including `bridges near U7 QFP fine pitch - reworked 9, rest shipped`. If the regenerated Line 2 tail no longer contains L2609–L2614, fix the `.tail(9)` selection to filter on `lot_id.isin(DRIFT_LOT_IDS)` plus the three preceding Line 2 lots.

- [ ] **Step 10: Commit**

```bash
git add data agent/tools/stats_verdict.py agent/tests/test_verdict_rule.py
git commit -m "feat: planted plant data with direction-aware verdict gate

check_plant.py now asserts instead of printing, shares the runtime verdict rule,
and proves the defect window is exactly L2609-L2614."
```

---

### Task 2: Quality documents and demo images

**Files:**
- Create: `prototype/backend/data/make_docs.py`
- Create: `prototype/backend/data/docs/pfmea.md`, `control_plan.md`, `past_8d_tombstoning.md`, `past_8d_voids.md` (generated)
- Create: `prototype/backend/data/images/IMAGES.md`
- Create: `prototype/backend/agent/tests/test_docs_corpus.py`

**Interfaces:**
- Consumes: `data.constants`.
- Produces: four markdown documents in `data/docs/`, each chunkable by a `## ` heading whose text is the citation `ref` (e.g. `## Row 14`, `## Item 6`). Task 4's `LocalDocSearch` and Task 12's `build_rag.py` both read this directory. `data/images/` holds the demo photos with per-file provenance.

- [ ] **Step 1: Write the failing test for the corpus**

`agent/tests/test_docs_corpus.py` — these assertions are the §10.5 acceptance criteria and the citations the writer prompt hard-codes.

```python
from pathlib import Path
import pytest

DOCS = Path(__file__).resolve().parents[2] / "data" / "docs"
FILES = ["pfmea.md", "control_plan.md", "past_8d_tombstoning.md", "past_8d_voids.md"]


@pytest.mark.parametrize("name", FILES)
def test_document_exists_and_is_labelled_synthetic(name):
    text = (DOCS / name).read_text()
    assert "Synthetic document for demo purposes" in text


def test_pfmea_row_14_is_the_planted_citation():
    text = (DOCS / "pfmea.md").read_text()
    assert "## Row 14" in text
    row14 = text.split("## Row 14")[1].split("## Row 15")[0]
    assert "Solder bridging" in row14
    assert "Reflow peak temperature above profile limit" in row14
    assert "Profile verification after any oven maintenance" in row14


def test_pfmea_has_twenty_numbered_rows():
    text = (DOCS / "pfmea.md").read_text()
    assert all(f"## Row {i}" in text for i in range(1, 21))


def test_control_plan_item_6_covers_profile_verification():
    text = (DOCS / "control_plan.md").read_text()
    assert "## Item 6" in text
    item6 = text.split("## Item 6")[1].split("## Item 7")[0]
    assert "Reflow profile verification after maintenance" in item6
    assert "hold lots" in item6 and "re-profile" in item6


def test_past_8d_links_to_the_closed_complaint():
    assert "C-2026-024" in (DOCS / "past_8d_tombstoning.md").read_text()


@pytest.mark.parametrize("name", FILES)
def test_every_section_has_a_citable_heading(name):
    lines = (DOCS / name).read_text().splitlines()
    assert any(line.startswith("## ") for line in lines)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_docs_corpus.py -v`
Expected: FAIL — `FileNotFoundError` for `data/docs/pfmea.md`

- [ ] **Step 3: Write `data/make_docs.py`**

Generate markdown rather than PDF (PRD §10.5 permits it and it keeps chunking exact). Every document ends with the footer `*Synthetic document for demo purposes.*`, and every citable unit is a `## ` heading so `ref` strings like `Row 14` and `Item 6` fall straight out of the chunker.

The PFMEA writes 20 rows for SMT reflow in AIAG-VDA 2019 style. Rows 1–13 and 15–20 cover ordinary SMT failure modes (insufficient paste, tombstoning, voids, misalignment, cold joint, component shift, warped board, nozzle wear, insufficient reflow, excess voiding, head-in-pillow, solder balls, stencil blockage, conveyor vibration, oxidation, moisture sensitivity, polarity reversal, missing component, AOI false call). **Row 14 is fixed verbatim:**

```python
ROW_14 = {
    "process_step": "Reflow soldering",
    "failure_mode": "Solder bridging",
    "effect": "Short circuit between adjacent pins; ECU functional failure at customer ICT",
    "severity": 8,
    "cause": "Reflow peak temperature above profile limit",
    "occurrence": 3,
    "prevention": "Profile verification after any oven maintenance",
    "detection_control": "AOI 100% + profile check per shift",
    "detection": 4,
    "ap": "High",
}
```

Each row renders as:

```markdown
## Row 14

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Solder bridging |
| Effect | Short circuit between adjacent pins; ECU functional failure at customer ICT |
| Severity | 8 |
| Cause | Reflow peak temperature above profile limit |
| Occurrence | 3 |
| Prevention control | Profile verification after any oven maintenance |
| Detection control | AOI 100% + profile check per shift |
| Detection | 4 |
| Action priority | High |
```

The control plan writes 12 items for the SMT line. **Item 6 is fixed verbatim:** characteristic `Reflow profile verification after maintenance`, specification `Peak temperature 235-250 °C, TAL 45-90 s, measured with a profiling board`, method `Profiler run on a golden board`, frequency `After any oven maintenance and once per shift`, reaction plan `hold lots produced since the last verified profile, re-profile the oven, re-qualify before release`. The remaining items cover paste inspection, SPI, placement accuracy, AOI, ICT, stencil cleaning, squeegee pressure, paste storage, nitrogen purity, conveyor speed and first-article checks.

Past 8D #1 (`past_8d_tombstoning.md`): D1–D8 for tombstoning on 0402 resistors traced to paste age beyond its working window, referencing complaint `C-2026-024`, lot `L2389`, customer `Hoshino Denso (fictional)`, closed with CAPA-0098. Past 8D #2 (`past_8d_voids.md`): voids under a QFN traced to a nitrogen supply regulator drift, CAPA-0111. Both use `## D1` … `## D8` headings.

```bash
python -m data.make_docs
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest agent/tests/test_docs_corpus.py -v`
Expected: 11 passed

- [ ] **Step 5: Collect the demo images**

PRD §10.4 needs 3–5 images that read as defects plus one clean board for the `insufficient_evidence` edge case. Download the VisA PCB subsets (CC BY 4.0 — read the licence page at download time), pick candidates, and save them as `data/images/defect_01.jpg` … `defect_05.jpg` and `no_defect_01.jpg`.

Write `data/images/IMAGES.md` with one row per file: filename, dataset, licence, URL, and why it was chosen. PRD §10.4: if no VisA image reliably reads as a solder bridge, photograph a real board on the team's bench and say so in this file and in the README.

- [ ] **Step 6: Pre-test the images against the vision prompt**

Before writing any vision code, paste the §9.4 vision prompt into Google AI Studio with each candidate image and record what comes back. Add a `Gemini reads it as` column to `IMAGES.md`. Keep only images where the answer is stable across two runs. This is the §17 mitigation for "vision misreads VisA images" and it costs ten minutes now instead of a failed demo later.

- [ ] **Step 7: Commit**

```bash
git add data/make_docs.py data/docs data/images agent/tests/test_docs_corpus.py
git commit -m "feat: synthetic PFMEA, control plan and past 8Ds + vetted demo images"
```

---

### Task 3: Plant data access — CSV and BigQuery behind one protocol

**Files:**
- Create: `prototype/backend/agent/tools/plant_data.py`
- Create: `prototype/backend/agent/tests/test_plant_data.py`

**Interfaces:**
- Consumes: `data.constants`, `agent.config.get_settings`.
- Produces:
  - `PlantStore` protocol with `lots()`, `process()`, `maintenance()`, `complaints()` → `pd.DataFrame`
  - `get_store() -> PlantStore` (honours `PLANT_BACKEND`)
  - `get_lot_genealogy(lot_id: str) -> dict`
  - `get_process_window(product: str = PRODUCT, days: int = 30) -> dict`
  - `get_maintenance_events(line: str, since: str | None = None) -> list[dict]`
  - `get_comparison_groups(lot_id: str, product: str = PRODUCT, days: int = 30) -> dict` returning `{"defect_lots": [...], "good_lots": [...], "defect_rate_threshold": float}`
  - `joined()` → lots ⨝ process with a `bridge_rate` column, used by Task 4

  Task 4's `test_hypothesis` and Task 8's investigator agent call these by exactly these names.

- [ ] **Step 1: Write the failing test**

`agent/tests/test_plant_data.py` — runs against the generated CSVs, no cloud (PRD Phase 3: "unit tests (CSV-based, no cloud)").

```python
import pytest
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT, PRODUCT
from agent.tools import plant_data as pd_tools


@pytest.fixture(scope="module")
def store():
    return pd_tools.CsvPlantStore()


def test_lots_cover_the_whole_window(store):
    lots = store.lots()
    assert len(lots) == 64
    assert set(lots.product) == {PRODUCT}


def test_lot_genealogy_returns_the_fields_the_8d_needs():
    g = pd_tools.get_lot_genealogy(GOLDEN_LOT)
    assert g["lot_id"] == GOLDEN_LOT
    assert g["line"] == "L2"
    assert g["defects_solder_bridge"] == 14
    assert {"shift", "operator_id", "stencil_id", "paste_lot", "qty", "date"} <= set(g)


def test_comparison_groups_split_defect_from_good():
    groups = pd_tools.get_comparison_groups(GOLDEN_LOT)
    assert sorted(groups["defect_lots"]) == sorted(DRIFT_LOT_IDS)
    assert GOLDEN_LOT in groups["defect_lots"]
    assert not set(groups["defect_lots"]) & set(groups["good_lots"])
    assert len(groups["good_lots"]) > 40


def test_maintenance_events_find_the_escape_point():
    events = pd_tools.get_maintenance_events("L2")
    wo388 = next(e for e in events if e["wo_id"] == "WO-388")
    assert wo388["post_check"] == "profile_verification_pending"
    assert "zone 7" in wo388["description"].lower()


def test_process_window_lists_testable_parameters():
    w = pd_tools.get_process_window()
    assert "reflow_peak_temp_c" in w["parameters"]
    assert w["parameters"]["reflow_peak_temp_c"]["unit"] == "°C"
    assert w["limits"]["reflow_peak_temp_c"] == 250.0


def test_joined_adds_bridge_rate():
    df = pd_tools.joined()
    assert "bridge_rate" in df.columns
    assert df.loc[df.lot_id == GOLDEN_LOT, "bridge_rate"].iloc[0] > 0.012


def test_unknown_lot_raises_a_clear_error():
    with pytest.raises(KeyError, match="L9999"):
        pd_tools.get_lot_genealogy("L9999")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_plant_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.plant_data'`

- [ ] **Step 3: Write `agent/tools/plant_data.py`**

```python
"""Plant data behind one protocol. CSV for tests and the local demo, BigQuery for the
cloud run. Switch with PLANT_BACKEND. No LLM touches this file."""
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import pandas as pd

from agent.config import get_settings
from data.constants import (DEFECT_RATE_THRESHOLD, PARAM_UNITS, PRODUCT,
                            REFLOW_PEAK_LIMIT_C)

OUT = Path(__file__).resolve().parents[2] / "data" / "out"
TABLES = ("lots", "process", "maintenance", "complaints")
NUMERIC_PARAMS = [p for p in PARAM_UNITS if p != "operator_id"]


class PlantStore(Protocol):
    def lots(self) -> pd.DataFrame: ...
    def process(self) -> pd.DataFrame: ...
    def maintenance(self) -> pd.DataFrame: ...
    def complaints(self) -> pd.DataFrame: ...


class CsvPlantStore:
    """Reads data/out/*.csv produced by data/generate_plant.py."""

    def _read(self, name: str) -> pd.DataFrame:
        path = OUT / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. Run `python -m data.generate_plant` first.")
        return pd.read_csv(path)

    def lots(self): return self._read("lots")
    def process(self): return self._read("process")
    def maintenance(self): return self._read("maintenance")
    def complaints(self): return self._read("complaints")


class BigQueryPlantStore:
    """Reads the BigQuery dataset loaded by infra/load_data.sh."""

    def __init__(self):
        from google.cloud import bigquery
        s = get_settings()
        self._client = bigquery.Client(project=s.gcp_project)
        self._dataset = f"{s.gcp_project}.{s.bq_dataset}"

    def _read(self, name: str) -> pd.DataFrame:
        return self._client.query(f"SELECT * FROM `{self._dataset}.{name}`").to_dataframe()

    def lots(self): return self._read("lots")
    def process(self): return self._read("process")
    def maintenance(self): return self._read("maintenance")
    def complaints(self): return self._read("complaints")


@lru_cache
def get_store() -> PlantStore:
    return BigQueryPlantStore() if get_settings().plant_backend == "bigquery" else CsvPlantStore()


@lru_cache
def joined() -> pd.DataFrame:
    store = get_store()
    df = store.lots().merge(store.process(), on="lot_id")
    df["date"] = pd.to_datetime(df["date"])
    df["bridge_rate"] = df.defects_solder_bridge / df.qty
    return df


def get_lot_genealogy(lot_id: str) -> dict:
    df = joined()
    hit = df[df.lot_id == lot_id]
    if hit.empty:
        raise KeyError(f"unknown lot {lot_id}")
    row = hit.iloc[0]
    return {
        "lot_id": row.lot_id, "line": row.line, "shift": row.shift,
        "date": row.date.strftime("%Y-%m-%d"), "product": row["product"], "qty": int(row.qty),
        "paste_lot": row.paste_lot, "stencil_id": row.stencil_id, "operator_id": row.operator_id,
        "defects_solder_bridge": int(row.defects_solder_bridge),
        "defects_other": int(row.defects_other),
        "bridge_rate": round(float(row.bridge_rate), 4), "ship_status": row.ship_status,
    }


def get_process_window(product: str = PRODUCT, days: int = 30) -> dict:
    df = joined()
    df = df[df["product"] == product]
    cutoff = df.date.max() - pd.Timedelta(days=days)
    df = df[df.date >= cutoff]
    return {
        "product": product,
        "days": days,
        "n_lots": int(len(df)),
        "parameters": {
            p: {"unit": PARAM_UNITS[p], "mean": round(float(df[p].mean()), 2),
                "min": round(float(df[p].min()), 2), "max": round(float(df[p].max()), 2)}
            for p in NUMERIC_PARAMS
        },
        "categorical": {"operator_id": sorted(df.operator_id.unique().tolist()),
                        "stencil_id": sorted(df.stencil_id.unique().tolist()),
                        "line": sorted(df.line.unique().tolist())},
        "limits": {"reflow_peak_temp_c": REFLOW_PEAK_LIMIT_C},
    }


def get_maintenance_events(line: str, since: str | None = None) -> list[dict]:
    m = get_store().maintenance()
    m = m[m.line == line]
    if since:
        m = m[pd.to_datetime(m.date) >= pd.Timestamp(since)]
    return m.sort_values("date").to_dict("records")


def get_comparison_groups(lot_id: str, product: str = PRODUCT, days: int = 30) -> dict:
    """Defect lots vs good lots of the same product in the last `days` (PRD 9.3)."""
    df = joined()
    df = df[df["product"] == product]
    cutoff = df.date.max() - pd.Timedelta(days=days)
    df = df[df.date >= cutoff]
    defect = df[df.bridge_rate > DEFECT_RATE_THRESHOLD]
    good = df[df.bridge_rate <= DEFECT_RATE_THRESHOLD]
    return {
        "lot_id": lot_id,
        "defect_lots": sorted(defect.lot_id.tolist()),
        "good_lots": sorted(good.lot_id.tolist()),
        "defect_rate_threshold": DEFECT_RATE_THRESHOLD,
        "window_days": days,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_plant_data.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add agent/tools/plant_data.py agent/tests/test_plant_data.py
git commit -m "feat: plant data access with CSV and BigQuery backends"
```

---

### Task 4: The statistics tool — the only thing that produces a verdict

**Files:**
- Create: `prototype/backend/agent/tools/charts.py`
- Create: `prototype/backend/agent/tools/storage.py`
- Create: `prototype/backend/agent/tools/stats_test.py`
- Create: `prototype/backend/agent/tests/test_stats_test.py`

**Interfaces:**
- Consumes: `agent.tools.stats_verdict.classify`, `agent.tools.plant_data` (`joined`, `get_comparison_groups`, `get_maintenance_events`), `data.constants` (`MIN_EFFECT`, `PARAM_UNITS`, `REFLOW_PEAK_LIMIT_C`, `WO388_DATE`), `agent.models.HypothesisResult`.
- Produces:
  - `agent.tools.storage.put_bytes(data: bytes, key: str, content_type: str) -> str` returning a URL (`/api/files/<key>` locally, a GCS URL when `FILES_BACKEND=gcs`)
  - `agent.tools.charts.render_reflow_chart(defect_lots: list[str], event_date: str | None = None, event_label: str = "") -> str` returning a chart URL
  - `agent.tools.stats_test.test_hypothesis(hypothesis_id, lot_id, parameter=None, event_wo_id=None, direction="any") -> HypothesisResult`

  Task 9's investigator agent calls `test_hypothesis` as its only verdict source.

- [ ] **Step 1: Write `agent/tools/storage.py`**

```python
"""Bytes in, URL out. Local files in dev, Cloud Storage when FILES_BACKEND=gcs."""
from pathlib import Path

from agent.config import get_settings

LOCAL_DIR = Path(__file__).resolve().parents[2] / "data" / "out" / "files"


def put_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    s = get_settings()
    if s.files_backend == "gcs":
        from google.cloud import storage
        blob = storage.Client(project=s.gcp_project).bucket(s.gcs_bucket).blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"https://storage.googleapis.com/{s.gcs_bucket}/{key}"
    path = LOCAL_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/api/files/{key}"


def get_local_path(key: str) -> Path:
    return LOCAL_DIR / key
```

- [ ] **Step 2: Write `agent/tools/charts.py`**

This is the §7 screen-3 chart: reflow peak temperature by lot, Line 2 highlighted, defect lots marked, a vertical line at the WO-388 date and a horizontal line at the 250 °C limit.

```python
"""Charts come from the data, never from the model."""
import hashlib
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agent.tools.plant_data import joined
from agent.tools.storage import put_bytes
from data.constants import REFLOW_PEAK_LIMIT_C

GREEN, GREY, AMBER, RED = "#1b5e3f", "#9aa5a0", "#b7791f", "#a6281f"


def render_reflow_chart(defect_lots: list[str], event_date: str | None = None,
                        event_label: str = "") -> str:
    df = joined().sort_values("date")
    key_src = f"{sorted(defect_lots)}|{event_date}|{event_label}".encode()
    key = f"charts/reflow_{hashlib.sha1(key_src).hexdigest()[:10]}.png"

    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=160)
    for line, colour, marker in (("L1", GREY, "o"), ("L2", GREEN, "s")):
        sub = df[df.line == line]
        ax.plot(sub.date, sub.reflow_peak_temp_c, marker, ms=4.5, lw=0,
                color=colour, label=f"Line {line[-1]}")

    bad = df[df.lot_id.isin(defect_lots)]
    ax.plot(bad.date, bad.reflow_peak_temp_c, "s", ms=9, mfc="none", mec=RED, mew=1.6,
            lw=0, label="Defect lots")

    ax.axhline(REFLOW_PEAK_LIMIT_C, color=AMBER, ls="--", lw=1.2)
    ax.annotate(f"{REFLOW_PEAK_LIMIT_C:.0f} °C profile limit",
                xy=(df.date.min(), REFLOW_PEAK_LIMIT_C), xytext=(0, 4),
                textcoords="offset points", color=AMBER, fontsize=8)
    if event_date:
        ax.axvline(pd.Timestamp(event_date), color=RED, ls=":", lw=1.4)
        ax.annotate(event_label or event_date, xy=(pd.Timestamp(event_date), ax.get_ylim()[1]),
                    xytext=(4, -12), textcoords="offset points", color=RED, fontsize=8)

    ax.set_ylabel("Reflow peak temp (°C)", fontsize=9)
    ax.set_xlabel("Lot date", fontsize=9)
    ax.set_title("Reflow peak temperature by lot — synthetic demo data", fontsize=10)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower left")
    ax.grid(alpha=0.25, lw=0.6)
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return put_bytes(buf.getvalue(), key, "image/png")
```

- [ ] **Step 2b: Eyeball the chart once**

```bash
python -c "
from data.constants import DRIFT_LOT_IDS, WO388_DATE
from agent.tools.charts import render_reflow_chart
print(render_reflow_chart(DRIFT_LOT_IDS, WO388_DATE, 'WO-388 maintenance'))"
open data/out/files/charts/*.png
```

Expected: the red-ringed defect lots all sit to the right of the dotted WO-388 line and above the amber 250 °C limit. If they do not, Task 1 regressed — rerun `python -m data.check_plant`.

- [ ] **Step 3: Write the failing test**

`agent/tests/test_stats_test.py` — the five §10.3 verdicts, now through the real tool rather than the data gate.

```python
import pytest
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT, WO388_ID
from agent.tools.stats_test import test_hypothesis


@pytest.fixture(scope="module")
def h2():
    return test_hypothesis("H2", GOLDEN_LOT, parameter="reflow_peak_temp_c",
                           event_wo_id=WO388_ID, direction="higher")


def test_h2_reflow_drift_is_supported(h2):
    assert h2.verdict == "supported"
    assert h2.p_value < 0.01
    assert h2.effect_value > 3.0
    assert h2.effect_unit == "°C"
    assert h2.test.startswith("Welch")


def test_h2_reports_group_sizes_and_a_chart(h2):
    assert h2.n_defect == len(DRIFT_LOT_IDS)
    assert h2.n_good > 40
    assert h2.chart_url and h2.chart_url.endswith(".png")


def test_h2_effect_string_carries_sign_and_unit(h2):
    assert h2.effect.startswith("+") and "°C" in h2.effect


def test_h1_stencil_wear_is_rejected_on_direction():
    r = test_hypothesis("H1", GOLDEN_LOT, parameter="stencil_print_count", direction="higher")
    assert r.verdict == "rejected"
    assert r.effect_value < 0


def test_h3_humidity_is_rejected():
    r = test_hypothesis("H3", GOLDEN_LOT, parameter="room_humidity_pct", direction="higher")
    assert r.verdict == "rejected"


def test_h4_operator_is_inconclusive_and_uses_fisher():
    r = test_hypothesis("H4", GOLDEN_LOT, parameter="operator_id", direction="higher")
    assert r.verdict == "inconclusive"
    assert r.test == "Fisher exact"
    assert 0.01 <= r.p_value <= 0.1


def test_paste_age_is_rejected():
    r = test_hypothesis("H5", GOLDEN_LOT, parameter="paste_age_h", direction="higher")
    assert r.verdict == "rejected"


def test_event_only_hypothesis_defaults_to_the_reflow_parameter():
    r = test_hypothesis("H6", GOLDEN_LOT, event_wo_id=WO388_ID, direction="higher")
    assert r.verdict == "supported"
    assert "before" in " ".join(r.group_labels).lower()


def test_unknown_parameter_raises():
    with pytest.raises(ValueError, match="not a testable parameter"):
        test_hypothesis("H7", GOLDEN_LOT, parameter="vibes", direction="higher")


def test_no_parameter_and_no_event_raises():
    with pytest.raises(ValueError, match="parameter or event"):
        test_hypothesis("H8", GOLDEN_LOT)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `pytest agent/tests/test_stats_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.stats_test'`

- [ ] **Step 5: Write `agent/tools/stats_test.py`**

```python
"""test_hypothesis — PRD 9.3. No LLM inside this file.

Comparison groups
  parameter hypothesis : defect lots vs good lots, same product, last 30 days  -> Welch t-test
  event hypothesis     : same line, lots before vs after the event date        -> Welch t-test
  categorical (operator): share of that operator in defect vs good lots        -> Fisher exact
"""
import pandas as pd
from scipy import stats

from agent.models import Direction, HypothesisResult
from agent.tools.charts import render_reflow_chart
from agent.tools.plant_data import (NUMERIC_PARAMS, get_comparison_groups,
                                    get_maintenance_events, joined)
from agent.tools.stats_verdict import classify
from data.constants import MIN_EFFECT, PARAM_UNITS

CATEGORICAL_PARAMS = {"operator_id", "stencil_id", "paste_lot"}
DEFAULT_EVENT_PARAM = "reflow_peak_temp_c"


def _fmt(value: float, unit: str) -> str:
    digits = 0 if abs(value) >= 1000 else (2 if abs(value) < 1 else 1)
    return f"{value:+,.{digits}f} {unit}"


def _numeric(df_a: pd.DataFrame, df_b: pd.DataFrame, param: str, direction: Direction,
             labels: list[str], hypothesis_id: str, chart_url: str | None) -> HypothesisResult:
    a, b = df_a[param].astype(float), df_b[param].astype(float)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    effect = float(a.mean() - b.mean())
    unit = PARAM_UNITS[param]
    return HypothesisResult(
        hypothesis_id=hypothesis_id,
        verdict=classify(float(p), effect, direction, MIN_EFFECT[param]),
        test="Welch t-test", p_value=round(float(p), 6),
        effect=f"{_fmt(effect, unit)} mean {param.replace('_', ' ')}",
        effect_value=round(effect, 3), effect_unit=unit,
        n_defect=int(len(a)), n_good=int(len(b)),
        group_labels=labels, chart_url=chart_url)


def _categorical(df: pd.DataFrame, defect_ids: list[str], param: str, direction: Direction,
                 hypothesis_id: str) -> HypothesisResult:
    is_defect = df.lot_id.isin(defect_ids)
    # The level most over-represented among the defect lots is the one being accused.
    level = df[is_defect][param].value_counts().idxmax()
    table = pd.crosstab(df[param] == level, is_defect)
    # Reindex so a missing cell becomes 0 rather than a KeyError.
    table = table.reindex(index=[False, True], columns=[False, True], fill_value=0)
    _, p = stats.fisher_exact(table.values)
    share_defect = float((df[is_defect][param] == level).mean())
    share_good = float((df[~is_defect][param] == level).mean())
    effect = share_defect - share_good
    return HypothesisResult(
        hypothesis_id=hypothesis_id,
        verdict=classify(float(p), effect, direction, MIN_EFFECT.get(param, 0.15)),
        test="Fisher exact", p_value=round(float(p), 6),
        effect=f"{effect:+.2f} share of {level} lots "
               f"({share_defect:.0%} of defect lots vs {share_good:.0%} of good lots)",
        effect_value=round(effect, 3), effect_unit="share of lots",
        n_defect=int(is_defect.sum()), n_good=int((~is_defect).sum()),
        group_labels=[f"{level} lots", "other lots"], chart_url=None)


def test_hypothesis(hypothesis_id: str, lot_id: str, parameter: str | None = None,
                    event_wo_id: str | None = None,
                    direction: Direction = "any") -> HypothesisResult:
    if not parameter and not event_wo_id:
        raise ValueError("a hypothesis needs one measurable parameter or event")
    if parameter and parameter not in PARAM_UNITS:
        raise ValueError(f"{parameter!r} is not a testable parameter. "
                         f"Choose one of: {', '.join(sorted(PARAM_UNITS))}")

    df = joined()
    groups = get_comparison_groups(lot_id)
    defect_ids = groups["defect_lots"]

    if event_wo_id:
        param = parameter if parameter in NUMERIC_PARAMS else DEFAULT_EVENT_PARAM
        wo = next((e for e in get_maintenance_events(df[df.lot_id == lot_id].line.iloc[0])
                   if e["wo_id"] == event_wo_id), None)
        if wo is None:
            raise ValueError(f"no maintenance event {event_wo_id} on this line")
        when, line = pd.Timestamp(wo["date"]), wo["line"]
        same_line = df[df.line == line]
        after, before = same_line[same_line.date > when], same_line[same_line.date <= when]
        if len(after) < 2 or len(before) < 2:
            raise ValueError(f"not enough lots either side of {event_wo_id} to test")
        chart = render_reflow_chart(defect_ids, wo["date"], f"{event_wo_id} maintenance")
        return _numeric(after, before, param, direction,
                        [f"Line {line[-1]} after {event_wo_id}",
                         f"Line {line[-1]} before {event_wo_id}"],
                        hypothesis_id, chart)

    if parameter in CATEGORICAL_PARAMS:
        return _categorical(df, defect_ids, parameter, direction, hypothesis_id)

    defect_df = df[df.lot_id.isin(defect_ids)]
    good_df = df[df.lot_id.isin(groups["good_lots"])]
    chart = render_reflow_chart(defect_ids) if parameter == DEFAULT_EVENT_PARAM else None
    return _numeric(defect_df, good_df, parameter, direction,
                    ["Defect lots", "Good lots (same product, 30 days)"],
                    hypothesis_id, chart)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest agent/tests/test_stats_test.py -v`
Expected: 10 passed

If `test_h4_operator_is_inconclusive_and_uses_fisher` fails, the dataset drifted — rerun the Task 1 Step 8 sweep rather than loosening the assertion. Loosening it would hand §17's "you planted the cause" objection straight to the judges.

- [ ] **Step 7: Commit**

```bash
git add agent/tools/stats_test.py agent/tools/charts.py agent/tools/storage.py agent/tests/test_stats_test.py
git commit -m "feat: direction-aware hypothesis testing with evidence chart"
```

---

### Task 5: Gemini client, prompts and the vision tool

**Files:**
- Create: `prototype/backend/agent/tools/llm.py`
- Create: `prototype/backend/agent/prompts/vision.md`, `intake.md`, `investigator.md`, `writer.md`, `customer_reply.md`
- Create: `prototype/backend/agent/tools/vision_tool.py`
- Create: `prototype/backend/agent/tests/test_llm.py`, `prototype/backend/agent/tests/test_vision_tool.py`
- Create: `prototype/backend/agent/tests/fixtures/vision_solder_bridge.json`, `vision_clean_board.json`, `tiny.jpg`

**Interfaces:**
- Consumes: `agent.config`, `agent.models`.
- Produces:
  - `agent.tools.llm.generate_structured(prompt: str, schema: type[T], *, parts: list | None = None, temperature: float = 0.2) -> T` — one retry on validation failure, then raises `StructuredOutputError`
  - `agent.tools.llm.generate_text(prompt: str, *, temperature: float = 0.3) -> str`
  - `agent.tools.llm.embed(texts: list[str]) -> list[list[float]]`
  - `agent.tools.llm.load_prompt(name: str) -> str` reading `agent/prompts/<name>.md`
  - `agent.tools.vision_tool.analyze_defect_image(image_bytes: bytes, mime_type: str) -> Defect`

  Tasks 6–11 use `generate_structured`, `embed` and `load_prompt` for every model call. No other module may construct a `genai.Client`.

- [ ] **Step 1: Write the failing test for the LLM wrapper**

`agent/tests/test_llm.py` — tests the contract around the model call, not the model.

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.llm'`

- [ ] **Step 3: Write `agent/tools/llm.py`**

```python
"""The only place a Gemini client is constructed. Model IDs come from env, never from code."""
import json
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
        except (ValidationError, json.JSONDecodeError) as exc:
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_llm.py -v`
Expected: 5 passed

- [ ] **Step 5: Write `agent/prompts/vision.md`**

PRD §9.4, verbatim requirements.

```markdown
You are an automated optical inspection assistant for SMT printed circuit board assembly.

Look ONLY at what is visible in the image. Report the single most important defect.

Rules:
- `type` must be one of: solder_bridge, missing_component, misalignment, scratch,
  contamination, other, none. Use `none` when the board looks acceptable.
- `severity`: critical = a short circuit or a safety risk; major = functional failure;
  minor = cosmetic only; none = no defect found.
- `box` is [x, y, width, height] as fractions of the image between 0 and 1, around the
  single defect you are reporting. Use [0, 0, 0, 0] when type is `none`.
- `confidence` is 0 to 1, how sure you are of `type`.
- `visual_evidence` is ONE sentence describing only what you can see, for example
  "Continuous bright solder joining two adjacent fine-pitch pads at the lower left of the QFP."
- NEVER guess the cause. Do not mention temperature, stencils, operators, humidity, process
  settings or maintenance. You describe appearance only; other agents investigate causes.
- If the image is too blurred, too dark or not a circuit board, return type `none` with a
  low confidence and say so in `visual_evidence`.

Reply with JSON only.
```

- [ ] **Step 6: Write the remaining four prompts**

`agent/prompts/intake.md` — extract `customer`, `product`, `lot_id`, `defect`, `qty_affected`, `qty_shipped`, `eight_d_due` from raw complaint text; leave a field null rather than guessing; normalise lot references like `lot 2611` to `L2611`; dates as `YYYY-MM-DD`.

`agent/prompts/investigator.md` — PRD §9.4:

```markdown
You are a supplier quality engineer investigating a confirmed defect at an SMT plant.

Propose 3 to 5 hypotheses for the root cause, spread across the 6Ms
(Machine, Method, Material, Man, Measurement, Environment).

Hard rules:
- Every hypothesis MUST name exactly ONE parameter from the process table, or ONE
  maintenance event id, plus the direction you expect (`higher`, `lower` or `any`).
  A hypothesis with nothing measurable is not allowed.
- Check quality memory FIRST. If a similar past case is returned, make its confirmed cause
  your first hypothesis.
- You do NOT decide whether a hypothesis is true. For every hypothesis you must call
  `test_hypothesis`, and you must accept the verdict it returns, including when it
  contradicts what you expected.
- NEVER write a number yourself — no p-values, no temperatures, no counts, no percentages.
  Numbers come only from tool results.
- Never propose "operator error" as a root cause. An operator-related hypothesis must name
  a measurable difference, such as the share of lots run by one operator.

Available parameters: reflow_peak_temp_c, time_above_liquidus_s, preheat_ramp_c_per_s,
soak_time_s, conveyor_speed_cm_min, paste_age_h, room_humidity_pct, stencil_print_count,
squeegee_pressure_kg, operator_id, stencil_id, paste_lot.

Reply with JSON only.
```

`agent/prompts/writer.md` — PRD §9.4:

```markdown
You are an experienced supplier quality engineer writing an 8D report to a Japanese
automotive customer under IATF 16949.

Write D1 to D8. Rules:
- D3 names the exact lots placed on hold.
- D4 states the root cause, HOW it was verified (which test, which p-value, which effect
  size, which group sizes), and WHY it escaped detection.
- D5 and D6 give the permanent corrective action and how its effectiveness will be checked.
- D7 names the PFMEA row and control plan item to update, using the citations provided.
- D8 closes and recognises the team.
- NEVER write "operator error" as a root cause.
- Every factual sentence ends with a citation in brackets, for example [PFMEA row 14],
  [Control plan item 6], [Chart: reflow peak temp by lot], [Lot record L2611].
- You may ONLY use numbers that appear in the tool results given to you. If a number you
  want is not there, write the sentence without it. Inventing a number is a critical error.
- Plain, factual, customer-facing English. No marketing language.

If the tool results contain no supported hypothesis, do not write an 8D. Instead return the
`insufficient_evidence` form listing exactly which data would settle the question.

Reply with JSON only.
```

`agent/prompts/customer_reply.md` — PRD §9.4: short, polite business Japanese (keigo) and English; cover containment, root cause, permanent fix and the CAPA number; no numbers beyond those supplied; return `{"ja": "...", "en": "..."}`.

- [ ] **Step 7: Record vision fixtures so the tests never call a model**

```bash
mkdir -p agent/tests/fixtures
python - <<'PY'
import json, pathlib
from agent.tools.vision_tool import analyze_defect_image   # written in step 9
fx = pathlib.Path("agent/tests/fixtures")
for src, name in [("data/images/defect_01.jpg", "vision_solder_bridge.json"),
                  ("data/images/no_defect_01.jpg", "vision_clean_board.json")]:
    d = analyze_defect_image(pathlib.Path(src).read_bytes(), "image/jpeg")
    (fx / name).write_text(d.model_dump_json(indent=2))
    print(name, d.type, d.confidence)
PY
```

Also save a 1×1 JPEG as `agent/tests/fixtures/tiny.jpg` for tests that only need bytes:

```bash
python -c "
from PIL import Image; Image.new('RGB',(1,1),(200,200,200)).save('agent/tests/fixtures/tiny.jpg')
" 2>/dev/null || python - <<'PY'
import base64, pathlib
pathlib.Path("agent/tests/fixtures/tiny.jpg").write_bytes(base64.b64decode(
 "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
 "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
 "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="))
PY
```

Note in `README.md` that these fixtures are recorded model output, regenerated with the snippet above whenever the prompt changes.

- [ ] **Step 8: Write the failing test for the vision tool**

`agent/tests/test_vision_tool.py`:

```python
import json
from pathlib import Path

import pytest

from agent.models import Defect
from agent.tools import vision_tool

FX = Path(__file__).parent / "fixtures"


@pytest.fixture
def stub(monkeypatch):
    def _stub(fixture_name):
        payload = json.loads((FX / fixture_name).read_text())
        monkeypatch.setattr(vision_tool, "generate_structured",
                            lambda *a, **k: Defect.model_validate(payload))
    return _stub


def test_defect_image_returns_a_typed_defect(stub):
    stub("vision_solder_bridge.json")
    d = vision_tool.analyze_defect_image((FX / "tiny.jpg").read_bytes(), "image/jpeg")
    assert d.type == "solder_bridge"
    assert d.severity in ("critical", "major", "minor")
    assert 0.0 <= d.confidence <= 1.0
    assert len(d.visual_evidence) > 10


def test_clean_board_returns_none_type(stub):
    stub("vision_clean_board.json")
    d = vision_tool.analyze_defect_image((FX / "tiny.jpg").read_bytes(), "image/jpeg")
    assert d.type == "none"


def test_empty_image_bytes_raise_before_any_model_call():
    with pytest.raises(ValueError, match="empty image"):
        vision_tool.analyze_defect_image(b"", "image/jpeg")


def test_image_bytes_are_never_logged(caplog, stub):
    stub("vision_solder_bridge.json")
    with caplog.at_level("DEBUG"):
        vision_tool.analyze_defect_image(b"\xff\xd8\xff\xe0SECRETBYTES", "image/jpeg")
    assert "SECRETBYTES" not in caplog.text
```

- [ ] **Step 9: Run the test to verify it fails, then write `agent/tools/vision_tool.py`**

Run: `pytest agent/tests/test_vision_tool.py -v` → FAIL, `ModuleNotFoundError`.

```python
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
```

Run: `pytest agent/tests/test_vision_tool.py -v`
Expected: 4 passed

- [ ] **Step 10: Confirm latency against the real model**

PRD §13 requires the defect box inside 10 s.

```bash
python - <<'PY'
import pathlib, time
from agent.tools.vision_tool import analyze_defect_image
img = pathlib.Path("data/images/defect_01.jpg").read_bytes()
t0 = time.time(); d = analyze_defect_image(img, "image/jpeg"); dt = time.time() - t0
print(f"{dt:.1f}s  {d.type} {d.severity} {d.confidence:.2f}  box={d.box}")
assert dt < 10, "vision is too slow for the PRD 13 latency budget"
PY
```

If it exceeds 10 s, shrink the image to 1024 px on the long edge before sending and record that in `vision_tool.py`.

- [ ] **Step 11: Commit**

```bash
git add agent/tools/llm.py agent/tools/vision_tool.py agent/prompts agent/tests
git commit -m "feat: Gemini client with structured output, prompts and vision tool"
```

---

### Task 6: Quality-document search with citations

**Files:**
- Create: `prototype/backend/agent/tools/doc_search.py`
- Create: `prototype/backend/agent/tests/test_doc_search.py`
- Create: `prototype/backend/infra/build_rag.py`

**Interfaces:**
- Consumes: `agent.tools.llm.embed`, `data/docs/*.md`.
- Produces: `agent.tools.doc_search.search_quality_docs(query: str, k: int = 3) -> list[Passage]`, honouring `DOCS_BACKEND`. `Passage.ref` is the heading text (`Row 14`, `Item 6`, `D4`); `Passage.source` is the filename. Task 9's evidence agent is the only caller.

- [ ] **Step 1: Write the failing test**

`agent/tests/test_doc_search.py`:

```python
import pytest
from agent.tools import doc_search


def test_chunking_splits_on_citable_headings():
    chunks = doc_search.chunk_documents()
    refs = {(c.source, c.ref) for c in chunks}
    assert ("pfmea.md", "Row 14") in refs
    assert ("control_plan.md", "Item 6") in refs
    assert len(chunks) > 40


def test_every_chunk_carries_its_quote():
    for c in doc_search.chunk_documents():
        assert c.quote.strip()
        assert len(c.quote) <= 600


def test_meaning_based_match_finds_pfmea_row_14():
    """PRD 4: 'solder bridging' must match 'peak temperature above limit' by meaning."""
    hits = doc_search.search_quality_docs(
        "solder bridging caused by reflow peak temperature above the profile limit", k=3)
    top = hits[0]
    assert top.source == "pfmea.md"
    assert top.ref == "Row 14"
    assert "Solder bridging" in top.quote


def test_profile_verification_query_finds_control_plan_item_6():
    hits = doc_search.search_quality_docs(
        "what must be done to the reflow profile after oven maintenance", k=3)
    assert any(h.source == "control_plan.md" and h.ref == "Item 6" for h in hits)


def test_k_is_respected():
    assert len(doc_search.search_quality_docs("solder bridging", k=2)) == 2


def test_empty_query_raises():
    with pytest.raises(ValueError, match="empty query"):
        doc_search.search_quality_docs("  ")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_doc_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.doc_search'`

- [ ] **Step 3: Write `agent/tools/doc_search.py`**

The local backend is not a keyword fallback — it embeds with `EMBED_MODEL` through Vertex, so it satisfies the "must use Google AI models" rule on its own and is a genuine safety net for the RAG Engine corpus.

```python
"""Cited passages from the quality documents.

local  : chunk data/docs/*.md on `## ` headings, embed with EMBED_MODEL, cosine similarity
vertex : Vertex AI RAG Engine corpus built by infra/build_rag.py
Both return the same Passage shape so the evidence agent never knows which one ran.
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


@lru_cache
def chunk_documents() -> tuple[Passage, ...]:
    chunks: list[Passage] = []
    for path in sorted(DOCS.glob("*.md")):
        text = path.read_text()
        parts = re.split(r"^## (.+)$", text, flags=re.M)
        # parts = [preamble, heading1, body1, heading2, body2, ...]
        for heading, body in zip(parts[1::2], parts[2::2]):
            quote = " ".join(body.split())[:MAX_QUOTE]
            if quote:
                chunks.append(Passage(source=path.name, ref=heading.strip(), quote=quote))
    return tuple(chunks)


@lru_cache
def _chunk_matrix() -> np.ndarray:
    vectors = embed([f"{c.source} {c.ref}: {c.quote}" for c in chunk_documents()])
    m = np.array(vectors, dtype="float32")
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def _search_local(query: str, k: int) -> list[Passage]:
    q = np.array(embed([query])[0], dtype="float32")
    q /= np.linalg.norm(q)
    scores = _chunk_matrix() @ q
    chunks = chunk_documents()
    return [chunks[i].model_copy(update={"score": round(float(scores[i]), 4)})
            for i in np.argsort(-scores)[:k]]


def _search_vertex(query: str, k: int) -> list[Passage]:
    from vertexai import rag
    s = get_settings()
    resp = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=s.rag_corpus)],
        text=query, similarity_top_k=k)
    out: list[Passage] = []
    for ctx in resp.contexts.contexts:
        source = Path(getattr(ctx, "source_uri", "") or "").name or "quality-docs"
        quote = " ".join((ctx.text or "").split())[:MAX_QUOTE]
        match = re.match(r"^(Row \d+|Item \d+|D\d)\b", quote)
        out.append(Passage(source=source, ref=match.group(1) if match else source,
                           quote=quote, score=round(float(getattr(ctx, "score", 0.0)), 4)))
    return out


def search_quality_docs(query: str, k: int = 3) -> list[Passage]:
    if not query.strip():
        raise ValueError("empty query")
    backend = get_settings().docs_backend
    return _search_vertex(query, k) if backend == "vertex" else _search_local(query, k)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_doc_search.py -v`
Expected: 6 passed. These call the real embedding model — the first run takes a few seconds while the chunk matrix builds.

If `test_meaning_based_match_finds_pfmea_row_14` fails, the PFMEA row text is too terse to embed distinctly. Add the failure-mode and cause words into the row's rendered body in `data/make_docs.py` rather than weakening the assertion — PRD §4 names this exact match as the reason RAG is in the product.

- [ ] **Step 5: Write `infra/build_rag.py`**

PRD Phase 2 gate: "Test query returns PFMEA row 14 with source."

```python
"""Creates the Vertex AI RAG Engine corpus from data/docs and proves it answers.
Run once per project:  python -m infra.build_rag
"""
import os
from pathlib import Path

import vertexai
from vertexai import rag

from agent.tools.storage import put_bytes

PROJECT = os.environ["GCP_PROJECT"]
REGION = os.environ.get("VERTEX_REGION") or os.environ["GCP_REGION"]
BUCKET = os.environ["GCS_BUCKET"]
DOCS = Path(__file__).resolve().parents[1] / "data" / "docs"

vertexai.init(project=PROJECT, location=REGION)

uris = []
for path in sorted(DOCS.glob("*.md")):
    put_bytes(path.read_bytes(), f"docs/{path.name}", "text/markdown")
    uris.append(f"gs://{BUCKET}/docs/{path.name}")
    print("uploaded", path.name)

corpus = rag.create_corpus(
    display_name="quality-docs",
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model=os.environ["EMBED_MODEL"]))))
rag.import_files(corpus.name, uris, transformation_config=rag.TransformationConfig(
    chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=64)))

print(f"\nRAG_CORPUS={corpus.name}   <- put this in .env\n")

resp = rag.retrieval_query(rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
                           text="solder bridging caused by reflow peak temperature "
                                "above the profile limit", similarity_top_k=3)
for ctx in resp.contexts.contexts:
    print(f"- {getattr(ctx, 'source_uri', '?')}: {(ctx.text or '')[:160]}")

joined = " ".join(c.text or "" for c in resp.contexts.contexts)
assert "Solder bridging" in joined and "Row 14" in joined, \
    "corpus does not return PFMEA row 14 — check chunk size and document headings"
print("\nPhase 2 gate passed: test query returns PFMEA row 14 with its source.")
```

The RAG Engine Python surface moves faster than most Vertex APIs. If `vertexai.rag` does not import or `create_corpus` rejects these arguments, check the current docs and adjust — then record the working call in `README.md`. If it cannot be made to work today, keep `DOCS_BACKEND=local` (noted as a cut line) and move on; the evidence agent is unchanged either way.

- [ ] **Step 6: Commit**

```bash
git add agent/tools/doc_search.py agent/tests/test_doc_search.py infra/build_rag.py
git commit -m "feat: cited quality-document search, local embeddings and Vertex RAG"
```

---

### Task 7: Application state and quality memory

**Files:**
- Create: `prototype/backend/agent/state.py`
- Create: `prototype/backend/agent/tools/memory.py`
- Create: `prototype/backend/agent/tests/test_state.py`, `prototype/backend/agent/tests/test_memory.py`

**Interfaces:**
- Consumes: `agent.models`, `agent.tools.llm.embed`, `agent.tools.plant_data` (for the complaints list).
- Produces:
  - `agent.state.StateStore` protocol: `save_investigation(inv)`, `get_investigation(id) -> Investigation | None`, `append_event(inv_id, event)`, `events(inv_id) -> list[Event]`, `create_record(kind: str, payload: dict) -> str`, `get_record(kind, id) -> dict | None`, `save_memory(entry: MemoryEntry, vector: list[float])`, `search_memory(vector, defect_type, k) -> list[tuple[MemoryEntry, float]]`, `list_memory() -> list[MemoryEntry]`
  - `agent.state.get_state() -> StateStore` (honours `STATE_BACKEND`)
  - `agent.state.next_id(prefix: str) -> str` producing `CAPA-0142`-style ids from a counter
  - `agent.tools.memory.save_quality_memory(...) -> str` and `search_quality_memory(defect_type, query, k=2) -> list[MemoryEntry]`

  Tasks 9–11 use these for every write. PRD §13: Firestore is written only by the API.

- [ ] **Step 1: Write the failing test for the state store**

`agent/tests/test_state.py`:

```python
import pytest

from agent.models import Event, Investigation, MemoryEntry
from agent.state import MemoryStateStore, next_id


@pytest.fixture
def store():
    return MemoryStateStore()


def test_investigation_round_trips(store):
    inv = Investigation(id="inv_1", lot_id="L2611", status="running")
    store.save_investigation(inv)
    assert store.get_investigation("inv_1").lot_id == "L2611"


def test_unknown_investigation_returns_none(store):
    assert store.get_investigation("inv_nope") is None


def test_events_keep_their_order(store):
    for seq in range(3):
        store.append_event("inv_1", Event(seq=seq, ts="t", agent="system",
                                          type="step_started", title=f"s{seq}"))
    assert [e.seq for e in store.events("inv_1")] == [0, 1, 2]


def test_records_get_prefixed_sequential_ids(store):
    first = store.create_record("capa", {"summary": "a"})
    second = store.create_record("capa", {"summary": "b"})
    assert first.startswith("CAPA-") and second != first
    assert store.get_record("capa", first)["summary"] == "a"


def test_id_format_matches_the_demo_script():
    assert next_id("capa", start=142) == "CAPA-0142"
    assert next_id("work_order", start=412) == "WO-412"
    assert next_id("hold", start=77) == "H-77"


def test_memory_search_filters_by_defect_type(store):
    store.save_memory(MemoryEntry(id="m1", defect_type="solder_bridge",
                                  root_cause="reflow drift"), [1.0, 0.0])
    store.save_memory(MemoryEntry(id="m2", defect_type="tombstoning",
                                  root_cause="paste age"), [1.0, 0.0])
    hits = store.search_memory([1.0, 0.0], defect_type="solder_bridge", k=5)
    assert [m.id for m, _ in hits] == ["m1"]


def test_memory_search_ranks_by_similarity(store):
    store.save_memory(MemoryEntry(id="far", defect_type="x", root_cause="a"), [0.0, 1.0])
    store.save_memory(MemoryEntry(id="near", defect_type="x", root_cause="b"), [1.0, 0.0])
    hits = store.search_memory([1.0, 0.0], defect_type="x", k=2)
    assert hits[0][0].id == "near"
    assert hits[0][1] > hits[1][1]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.state'`

- [ ] **Step 3: Write `agent/state.py`**

```python
"""Investigations, records and quality memory. In-memory for tests and the local demo,
Firestore for the cloud run. Nothing outside the API writes here (PRD 13)."""
import itertools
import math
from functools import lru_cache
from typing import Protocol

from agent.config import get_settings
from agent.models import Event, Investigation, MemoryEntry

PREFIX = {"capa": "CAPA", "work_order": "WO", "hold": "H", "memory": "MEM"}
WIDTH = {"capa": 4, "work_order": 3, "hold": 2, "memory": 4}
# Demo ids follow the PRD 8 script: CAPA-0142, H-77, WO-412.
START = {"capa": 142, "work_order": 412, "hold": 77, "memory": 1}
_counters = {kind: itertools.count(start) for kind, start in START.items()}


def next_id(kind: str, start: int | None = None) -> str:
    n = start if start is not None else next(_counters[kind])
    return f"{PREFIX[kind]}-{n:0{WIDTH[kind]}d}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


class StateStore(Protocol):
    def save_investigation(self, inv: Investigation) -> None: ...
    def get_investigation(self, inv_id: str) -> Investigation | None: ...
    def append_event(self, inv_id: str, event: Event) -> None: ...
    def events(self, inv_id: str) -> list[Event]: ...
    def create_record(self, kind: str, payload: dict) -> str: ...
    def get_record(self, kind: str, record_id: str) -> dict | None: ...
    def save_memory(self, entry: MemoryEntry, vector: list[float]) -> None: ...
    def search_memory(self, vector: list[float], defect_type: str,
                      k: int) -> list[tuple[MemoryEntry, float]]: ...
    def list_memory(self) -> list[MemoryEntry]: ...


class MemoryStateStore:
    def __init__(self):
        self._inv: dict[str, Investigation] = {}
        self._events: dict[str, list[Event]] = {}
        self._records: dict[str, dict[str, dict]] = {}
        self._memory: list[tuple[MemoryEntry, list[float]]] = []

    def save_investigation(self, inv): self._inv[inv.id] = inv
    def get_investigation(self, inv_id): return self._inv.get(inv_id)
    def append_event(self, inv_id, event): self._events.setdefault(inv_id, []).append(event)
    def events(self, inv_id): return list(self._events.get(inv_id, []))

    def create_record(self, kind, payload):
        record_id = next_id(kind)
        self._records.setdefault(kind, {})[record_id] = {"id": record_id, **payload}
        return record_id

    def get_record(self, kind, record_id):
        return self._records.get(kind, {}).get(record_id)

    def save_memory(self, entry, vector): self._memory.append((entry, vector))

    def search_memory(self, vector, defect_type, k):
        scored = [(e, _cosine(vector, v)) for e, v in self._memory
                  if e.defect_type == defect_type]
        return sorted(scored, key=lambda t: -t[1])[:k]

    def list_memory(self): return [e for e, _ in self._memory]


class FirestoreStateStore:
    """Collections: investigations, events, capa, holds, work_orders, memory (PRD 11)."""

    COLLECTION = {"capa": "capa", "work_order": "work_orders", "hold": "holds"}

    def __init__(self):
        from google.cloud import firestore
        s = get_settings()
        self._db = firestore.Client(project=s.gcp_project, database=s.firestore_db)

    def save_investigation(self, inv):
        self._db.collection("investigations").document(inv.id).set(inv.model_dump())

    def get_investigation(self, inv_id):
        snap = self._db.collection("investigations").document(inv_id).get()
        return Investigation.model_validate(snap.to_dict()) if snap.exists else None

    def append_event(self, inv_id, event):
        (self._db.collection("investigations").document(inv_id)
         .collection("events").document(f"{event.seq:05d}").set(event.model_dump()))

    def events(self, inv_id):
        docs = (self._db.collection("investigations").document(inv_id)
                .collection("events").order_by("seq").stream())
        return [Event.model_validate(d.to_dict()) for d in docs]

    def create_record(self, kind, payload):
        record_id = next_id(kind)
        self._db.collection(self.COLLECTION[kind]).document(record_id).set(
            {"id": record_id, **payload})
        return record_id

    def get_record(self, kind, record_id):
        snap = self._db.collection(self.COLLECTION[kind]).document(record_id).get()
        return snap.to_dict() if snap.exists else None

    def save_memory(self, entry, vector):
        from google.cloud.firestore_v1.vector import Vector
        self._db.collection("memory").document(entry.id).set(
            {**entry.model_dump(), "embedding": Vector(vector)})

    def search_memory(self, vector, defect_type, k):
        from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
        from google.cloud.firestore_v1.vector import Vector
        query = (self._db.collection("memory").where("defect_type", "==", defect_type)
                 .find_nearest(vector_field="embedding", query_vector=Vector(vector),
                               distance_measure=DistanceMeasure.COSINE, limit=k,
                               distance_result_field="distance"))
        out = []
        for doc in query.stream():
            data = doc.to_dict()
            distance = float(data.pop("distance", 1.0))
            data.pop("embedding", None)
            out.append((MemoryEntry.model_validate(data), 1.0 - distance))
        return out

    def list_memory(self):
        out = []
        for doc in self._db.collection("memory").stream():
            data = doc.to_dict()
            data.pop("embedding", None)
            out.append(MemoryEntry.model_validate(data))
        return out


@lru_cache
def get_state() -> StateStore:
    return FirestoreStateStore() if get_settings().state_backend == "firestore" else MemoryStateStore()
```

The Firestore vector index must exist before `search_memory` works:

```bash
gcloud firestore indexes composite create \
  --collection-group=memory --query-scope=COLLECTION \
  --field-config=field-path=defect_type,order=ASCENDING \
  --field-config=field-path=embedding,vector-config='{"dimension":768,"flat":{}}' \
  --database='(default)'
```

Set `dimension` to whatever `EMBED_MODEL` actually returns — print `len(embed(["x"])[0])` and use that number.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_state.py -v`
Expected: 7 passed

- [ ] **Step 5: Write the failing test for quality memory**

`agent/tests/test_memory.py`:

```python
import pytest

from agent.state import MemoryStateStore
from agent.tools import memory as mem


@pytest.fixture(autouse=True)
def local(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr(mem, "get_state", lambda: store)
    # Deterministic pseudo-embeddings: same words -> same vector, no model call.
    monkeypatch.setattr(mem, "embed", lambda texts: [
        [float(t.lower().count(w)) for w in ("reflow", "temperature", "paste", "humidity")]
        for t in texts])
    return store


def test_saving_returns_an_id_and_lists_back():
    mid = mem.save_quality_memory(investigation_id="inv_1", defect_type="solder_bridge",
                                  root_cause="Reflow peak temperature drift after WO-388",
                                  parameter="reflow_peak_temp_c", line="L2",
                                  capa_id="CAPA-0142", lot_id="L2611")
    assert mid.startswith("MEM-")
    assert [e.root_cause for e in mem.list_quality_memory()] == [
        "Reflow peak temperature drift after WO-388"]


def test_similar_case_is_found_for_the_same_defect_type():
    mem.save_quality_memory(investigation_id="inv_1", defect_type="solder_bridge",
                            root_cause="Reflow peak temperature drift after WO-388",
                            parameter="reflow_peak_temp_c", line="L2",
                            capa_id="CAPA-0142", lot_id="L2611")
    hits = mem.search_quality_memory("solder_bridge", "reflow temperature too high", k=2)
    assert hits and hits[0].capa_id == "CAPA-0142"


def test_a_different_defect_type_does_not_match():
    mem.save_quality_memory(investigation_id="inv_1", defect_type="tombstoning",
                            root_cause="Paste past its working window",
                            parameter="paste_age_h", line="L1",
                            capa_id="CAPA-0098", lot_id="L2389")
    assert mem.search_quality_memory("solder_bridge", "reflow temperature too high") == []


def test_empty_memory_returns_empty_not_an_error():
    assert mem.search_quality_memory("solder_bridge", "anything") == []
```

- [ ] **Step 6: Run the test to verify it fails, then write `agent/tools/memory.py`**

Run: `pytest agent/tests/test_memory.py -v` → FAIL, `ModuleNotFoundError`.

```python
"""Quality memory: confirmed causes, found again by meaning rather than keyword (PRD 4)."""
from datetime import datetime, timezone

from agent.models import MemoryEntry
from agent.state import get_state, next_id
from agent.tools.llm import embed

MIN_SIMILARITY = 0.6


def _text(defect_type: str, root_cause: str, parameter: str, line: str) -> str:
    return f"{defect_type} on line {line}: {root_cause} (parameter {parameter})"


def save_quality_memory(*, investigation_id: str, defect_type: str, root_cause: str,
                        parameter: str = "", line: str = "", capa_id: str = "",
                        lot_id: str = "") -> str:
    entry = MemoryEntry(
        id=next_id("memory"), defect_type=defect_type, root_cause=root_cause,
        parameter=parameter, line=line, capa_id=capa_id, lot_id=lot_id,
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    vector = embed([_text(defect_type, root_cause, parameter, line)])[0]
    get_state().save_memory(entry, vector)
    return entry.id


def search_quality_memory(defect_type: str, query: str, k: int = 2) -> list[MemoryEntry]:
    vector = embed([query])[0]
    hits = get_state().search_memory(vector, defect_type=defect_type, k=k)
    return [entry for entry, score in hits if score >= MIN_SIMILARITY]


def list_quality_memory() -> list[MemoryEntry]:
    return get_state().list_memory()
```

Run: `pytest agent/tests/test_memory.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add agent/state.py agent/tools/memory.py agent/tests/test_state.py agent/tests/test_memory.py
git commit -m "feat: state store (memory + Firestore) and quality memory with vector search"
```

---

### Task 8: Intake — the complaint and the messy Excel

This is the §17 answer to "a Tier-2 plant has no MES", so the Excel parser has to survive the mess the generator deliberately creates: title rows above the header, `dd/mm` dates, short column names, and the literal string `same as prev` where a temperature should be.

**Files:**
- Create: `prototype/backend/agent/tools/intake_tools.py`
- Create: `prototype/backend/agent/tests/test_intake_tools.py`

**Interfaces:**
- Consumes: `agent.tools.llm.generate_structured`, `agent.models.Complaint`/`TravelerRow`, `agent.tools.plant_data.get_store`.
- Produces:
  - `parse_complaint(text: str, complaint_id: str = "") -> Complaint`
  - `parse_lot_traveler(xlsx_bytes: bytes) -> list[TravelerRow]`
  - `list_complaints() -> list[Complaint]` with `due_in_working_days` computed
  - `working_days_between(start: date, end: date) -> int`

  Task 9's intake agent and Task 10's `GET /complaints` are the callers.

- [ ] **Step 1: Write the failing test**

`agent/tests/test_intake_tools.py`:

```python
from datetime import date
from pathlib import Path

import pytest

from agent.models import Complaint
from agent.tools import intake_tools as it

XLSX = Path(__file__).resolve().parents[2] / "data" / "out" / "lot_traveler_line2_wk41.xlsx"


def test_working_days_skip_weekends():
    # Fri 16 Oct 2026 -> Mon 19 Oct 2026 is one working day.
    assert it.working_days_between(date(2026, 10, 16), date(2026, 10, 19)) == 1
    assert it.working_days_between(date(2026, 10, 16), date(2026, 10, 29)) == 9
    assert it.working_days_between(date(2026, 10, 29), date(2026, 10, 16)) == -9


def test_complaint_parsing_pulls_the_fields(monkeypatch):
    monkeypatch.setattr(it, "generate_structured", lambda *a, **k: Complaint(
        complaint_id="", customer="Hoshino Denso (fictional)", product="ECU-PCB-7",
        lot_id="L2611", defect="solder_bridge", qty_affected=14, qty_shipped=500,
        eight_d_due="2026-10-29"))
    c = it.parse_complaint("Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units...",
                           complaint_id="C-2026-031")
    assert c.complaint_id == "C-2026-031"
    assert c.lot_id == "L2611"
    assert c.qty_affected == 14


def test_traveler_finds_the_header_below_the_title_rows():
    rows = it.parse_lot_traveler(XLSX.read_bytes())
    assert len(rows) >= 6
    assert all(r.lot_id.startswith("L") for r in rows)


def test_traveler_normalises_short_lot_numbers_and_dd_mm_dates():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert "L2611" in rows
    assert rows["L2611"].date.startswith("2026-")


def test_same_as_prev_becomes_null_and_is_flagged_low_confidence():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    r = rows["L2613"]
    assert r.reflow_peak_temp_c is None
    assert "reflow_peak_temp_c" in r.low_confidence_fields


def test_free_text_remarks_survive():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert "U7" in rows["L2611"].remarks


def test_traveler_bridge_counts_match_the_plant_record():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert rows["L2611"].aoi_bridges == 14


def test_a_file_that_is_not_a_spreadsheet_raises():
    with pytest.raises(ValueError, match="could not read"):
        it.parse_lot_traveler(b"this is not xlsx")


def test_complaints_list_carries_the_countdown():
    complaints = it.list_complaints()
    golden = next(c for c in complaints if c.complaint_id == "C-2026-031")
    assert golden.customer == "Hoshino Denso (fictional)"
    assert golden.due_in_working_days is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_intake_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.intake_tools'`

- [ ] **Step 3: Write `agent/tools/intake_tools.py`**

The header hunt and the `same as prev` handling are deterministic code, not a model call — they are cheap, exact, and the §13 latency budget has no room for an extra round trip. Gemini does the part only a model can do: turning free-text complaint prose into fields.

```python
"""Complaint text and the messy shift-lead spreadsheet, turned into typed rows."""
import io
import logging
import re
from datetime import date, datetime, timedelta

from openpyxl import load_workbook

from agent.models import Complaint, TravelerRow
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.plant_data import get_store

log = logging.getLogger(__name__)

# Short column names the shift leads actually type -> our field names.
COLUMN_ALIASES = {
    "lot#": "lot_id", "lot": "lot_id", "lot no": "lot_id",
    "dt": "date", "date": "date",
    "shift": "shift",
    "opr": "operator_id", "operator": "operator_id",
    "oven peak (c) [from printout]": "reflow_peak_temp_c", "oven peak": "reflow_peak_temp_c",
    "peak": "reflow_peak_temp_c", "peak (c)": "reflow_peak_temp_c",
    "tal sec": "time_above_liquidus_s", "tal": "time_above_liquidus_s",
    "aoi bridge": "aoi_bridges", "aoi bridges": "aoi_bridges", "bridges": "aoi_bridges",
    "remarks": "remarks", "remark": "remarks", "notes": "remarks",
}
NON_NUMERIC = re.compile(r"[^0-9.\-]")
DEFAULT_YEAR = 2026


def working_days_between(start: date, end: date) -> int:
    """Signed count of Mon-Fri days strictly after `start` up to and including `end`."""
    sign = 1 if end >= start else -1
    lo, hi = (start, end) if sign == 1 else (end, start)
    days = sum(1 for n in range(1, (hi - lo).days + 1)
               if (lo + timedelta(days=n)).weekday() < 5)
    return sign * days


def _norm_lot(value) -> str:
    text = str(value).strip().upper()
    digits = re.sub(r"\D", "", text)
    return f"L{digits}" if digits else ""


def _norm_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    for fmt in ("%d/%m", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(year=DEFAULT_YEAR).date().isoformat() \
                if fmt == "%d/%m" else parsed.date().isoformat()
        except ValueError:
            continue
    return ""


def _norm_number(value) -> float | None:
    """Returns None for anything the shift lead wrote instead of a number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = NON_NUMERIC.sub("", str(value))
    try:
        return float(cleaned) if cleaned not in ("", "-", ".") else None
    except ValueError:
        return None


def parse_lot_traveler(xlsx_bytes: bytes) -> list[TravelerRow]:
    try:
        ws = load_workbook(io.BytesIO(xlsx_bytes), data_only=True).active
    except Exception as exc:
        raise ValueError(f"could not read the uploaded spreadsheet: {exc.__class__.__name__}")

    grid = [[c for c in row] for row in ws.iter_rows(values_only=True)]

    # Hunt for the header row: the first row where 2+ cells match a known column name.
    header_idx, mapping = None, {}
    for idx, row in enumerate(grid):
        found = {}
        for col, cell in enumerate(row):
            key = str(cell).strip().lower() if cell is not None else ""
            if key in COLUMN_ALIASES:
                found[COLUMN_ALIASES[key]] = col
        if len(found) >= 2:
            header_idx, mapping = idx, found
            break
    if header_idx is None:
        raise ValueError("could not read the uploaded spreadsheet: no recognisable header row")
    log.info("traveler header found on row %d, %d columns mapped",
             header_idx + 1, len(mapping))

    rows: list[TravelerRow] = []
    for raw in grid[header_idx + 1:]:
        if not any(cell not in (None, "") for cell in raw):
            continue
        def cell(field):
            col = mapping.get(field)
            return raw[col] if col is not None and col < len(raw) else None

        lot_id = _norm_lot(cell("lot_id"))
        if not lot_id:
            continue

        low: list[str] = []
        peak = _norm_number(cell("reflow_peak_temp_c"))
        if peak is None and cell("reflow_peak_temp_c") not in (None, ""):
            low.append("reflow_peak_temp_c")      # e.g. the literal "same as prev"
        tal = _norm_number(cell("time_above_liquidus_s"))
        if tal is None and cell("time_above_liquidus_s") not in (None, ""):
            low.append("time_above_liquidus_s")
        when = _norm_date(cell("date"))
        if not when and cell("date") not in (None, ""):
            low.append("date")

        bridges = _norm_number(cell("aoi_bridges"))
        rows.append(TravelerRow(
            lot_id=lot_id, date=when, shift=str(cell("shift") or "").strip(),
            operator_id=str(cell("operator_id") or "").strip(),
            reflow_peak_temp_c=peak, time_above_liquidus_s=tal,
            aoi_bridges=int(bridges) if bridges is not None else None,
            remarks=str(cell("remarks") or "").strip(), low_confidence_fields=low))
    return rows


def parse_complaint(text: str, complaint_id: str = "") -> Complaint:
    prompt = f"{load_prompt('intake')}\n\nComplaint text:\n{text}"
    parsed = generate_structured(prompt, Complaint, temperature=0.0)
    parsed.text = text
    if complaint_id:
        parsed.complaint_id = complaint_id
    if parsed.lot_id:
        parsed.lot_id = _norm_lot(parsed.lot_id)
    return parsed


def list_complaints(today: date | None = None) -> list[Complaint]:
    """The inbox. Parsed fields come from the dataset, so no model call per page load
    (PRD 7 screen 0: 'cached after first run')."""
    today = today or date.today()
    out: list[Complaint] = []
    for row in get_store().complaints().to_dict("records"):
        due = row.get("eight_d_due") or ""
        out.append(Complaint(
            complaint_id=row["complaint_id"], customer=row["customer"], product=row["product"],
            lot_id=row["lot_id"], defect=row["defect"], received=str(row.get("received", "")),
            eight_d_due=str(due), status=row.get("status", "open"), text=row.get("text", ""),
            due_in_working_days=working_days_between(today, date.fromisoformat(str(due)))
            if due else None))
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_intake_tools.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add agent/tools/intake_tools.py agent/tests/test_intake_tools.py
git commit -m "feat: complaint extraction and messy lot-traveler parsing"
```

---

### Task 9: Agents, event bus and the orchestrator

**Files:**
- Create: `prototype/backend/agent/events.py`
- Create: `prototype/backend/agent/tools/provenance.py`
- Create: `prototype/backend/agent/agents/intake.py`, `vision.py`, `investigator.py`, `evidence.py`, `writer.py`
- Create: `prototype/backend/agent/orchestrator.py`
- Create: `prototype/backend/agent/tests/test_events.py`, `test_provenance.py`, `test_orchestrator.py`

**Interfaces:**
- Consumes: every tool from Tasks 3–8.
- Produces:
  - `agent.events.EventBus` with `publish(inv_id, agent, type, title, detail="", data=None) -> Event` (awaitable), `subscribe(inv_id) -> AsyncIterator[Event]` (replays history, then streams live), `close(inv_id)`
  - `agent.events.bus` — the process-wide instance
  - `agent.orchestrator.run_investigation(inv_id: str) -> None` — the whole §8 golden path
  - `agent.tools.provenance.check_numbers(eight_d: EightD, allowed: set[str]) -> list[str]` and `allowed_numbers(inv: Investigation) -> set[str]`

  Task 10's `POST /investigations` schedules `run_investigation`; `GET /investigations/{id}/events` subscribes to `bus`.

- [ ] **Step 1: Write the failing test for the event bus**

The subtle requirement: the UI navigates to `/inv/:id` *after* the POST returns, so a subscriber that arrives late must still see every event from seq 0. A naive queue-only bus drops them.

`agent/tests/test_events.py`:

```python
import asyncio

import pytest

from agent.events import EventBus


async def _take(bus, inv_id, n):
    out = []
    async for event in bus.subscribe(inv_id):
        out.append(event)
        if len(out) == n:
            break
    return out


@pytest.mark.asyncio
async def test_sequence_numbers_start_at_zero_and_increment():
    bus = EventBus()
    a = await bus.publish("inv_1", "system", "step_started", "a")
    b = await bus.publish("inv_1", "vision", "tool_result", "b")
    assert (a.seq, b.seq) == (0, 1)


@pytest.mark.asyncio
async def test_sequences_are_per_investigation():
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "a")
    other = await bus.publish("inv_2", "system", "step_started", "a")
    assert other.seq == 0


@pytest.mark.asyncio
async def test_a_late_subscriber_still_receives_the_history():
    bus = EventBus()
    await bus.publish("inv_1", "system", "step_started", "first")
    await bus.publish("inv_1", "vision", "tool_result", "second")
    got = await asyncio.wait_for(_take(bus, "inv_1", 2), timeout=2)
    assert [e.title for e in got] == ["first", "second"]


@pytest.mark.asyncio
async def test_a_live_subscriber_receives_new_events():
    bus = EventBus()
    task = asyncio.create_task(_take(bus, "inv_1", 1))
    await asyncio.sleep(0.05)
    await bus.publish("inv_1", "writer", "draft_ready", "ready")
    assert (await asyncio.wait_for(task, timeout=2))[0].title == "ready"


@pytest.mark.asyncio
async def test_two_subscribers_both_receive_every_event():
    bus = EventBus()
    tasks = [asyncio.create_task(_take(bus, "inv_1", 1)) for _ in range(2)]
    await asyncio.sleep(0.05)
    await bus.publish("inv_1", "system", "done", "done")
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)
    assert all(r[0].title == "done" for r in results)


@pytest.mark.asyncio
async def test_timestamps_are_utc_iso():
    bus = EventBus()
    event = await bus.publish("inv_1", "system", "done", "done")
    assert event.ts.endswith("Z") and "T" in event.ts


@pytest.mark.asyncio
async def test_close_ends_the_stream():
    bus = EventBus()
    await bus.publish("inv_1", "system", "done", "done")
    bus.close("inv_1")
    got = [e async for e in bus.subscribe("inv_1")]
    assert len(got) == 1
```

- [ ] **Step 2: Run the test to verify it fails, then write `agent/events.py`**

Run: `pytest agent/tests/test_events.py -v` → FAIL, `ModuleNotFoundError`.

```python
"""One ordered event stream per investigation. History first, then live — so the UI can
subscribe after the POST returns and still see the whole run (PRD 12.3)."""
import asyncio
import itertools
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncIterator

from agent.models import Event
from agent.state import get_state


class EventBus:
    def __init__(self):
        self._history: dict[str, list[Event]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._seq: dict[str, itertools.count] = defaultdict(lambda: itertools.count())
        self._closed: set[str] = set()

    async def publish(self, inv_id: str, agent: str, type: str, title: str,
                      detail: str = "", data: dict | None = None) -> Event:
        event = Event(seq=next(self._seq[inv_id]),
                      ts=datetime.now(timezone.utc).isoformat(timespec="seconds")
                        .replace("+00:00", "Z"),
                      agent=agent, type=type, title=title, detail=detail, data=data or {})
        self._history[inv_id].append(event)
        get_state().append_event(inv_id, event)
        for queue in list(self._subscribers[inv_id]):
            queue.put_nowait(event)
        return event

    async def subscribe(self, inv_id: str) -> AsyncIterator[Event]:
        queue: asyncio.Queue = asyncio.Queue()
        replayed = len(self._history[inv_id])
        for event in self._history[inv_id][:replayed]:
            yield event
        if inv_id in self._closed:
            return
        self._subscribers[inv_id].append(queue)
        try:
            # Anything published between the snapshot and the subscribe lands in the queue;
            # skip what we already yielded.
            while True:
                event = await queue.get()
                if event.seq >= replayed:
                    yield event
                if event.type in ("done", "error"):
                    return
        finally:
            self._subscribers[inv_id].remove(queue)

    def history(self, inv_id: str) -> list[Event]:
        return list(self._history[inv_id])

    def close(self, inv_id: str) -> None:
        self._closed.add(inv_id)
        for queue in list(self._subscribers[inv_id]):
            queue.put_nowait(Event(seq=-1, ts="", agent="system", type="done", title="closed"))


bus = EventBus()
```

Run: `pytest agent/tests/test_events.py -v`
Expected: 7 passed

- [ ] **Step 3: Write the failing test for number provenance**

`agent/tests/test_provenance.py`:

```python
from agent.models import Citation, EightD, EightDSection, HypothesisResult, Investigation
from agent.tools.provenance import allowed_numbers, check_numbers


def _eight_d(d4_text: str) -> EightD:
    blank = EightDSection(text="Nothing numeric here.", citations=[])
    return EightD(D1=blank, D2=blank, D3=blank,
                  D4=EightDSection(text=d4_text, citations=[
                      Citation(label="PFMEA row 14", source="pfmea.md", ref="Row 14")]),
                  D5=blank, D6=blank, D7=blank, D8=blank)


def _inv() -> Investigation:
    return Investigation(id="inv_1", lot_id="L2611", results=[HypothesisResult(
        hypothesis_id="H2", verdict="supported", test="Welch t-test", p_value=0.003,
        effect="+8.2 °C mean reflow peak temp", effect_value=8.2, effect_unit="°C",
        n_defect=6, n_good=58)])


def test_numbers_from_tool_results_pass():
    inv = _inv()
    text = ("Peak temperature rose by 8.2 °C on Line 2 (Welch t-test, p = 0.003, "
            "6 defect lots vs 58 good lots) [Chart: reflow peak temp by lot].")
    assert check_numbers(_eight_d(text), allowed_numbers(inv)) == []


def test_an_invented_number_is_reported():
    inv = _inv()
    text = "Peak temperature rose by 12.7 °C [Chart: reflow peak temp by lot]."
    violations = check_numbers(_eight_d(text), allowed_numbers(inv))
    assert any("12.7" in v for v in violations)
    assert any("D4" in v for v in violations)


def test_citation_labels_and_lot_ids_are_allowed():
    inv = _inv()
    text = "Lots L2609 to L2614 are on hold [PFMEA row 14] [Control plan item 6]."
    assert check_numbers(_eight_d(text), allowed_numbers(inv) | {"2609", "2614", "14", "6"}) == []


def test_allowed_set_includes_p_value_effect_and_group_sizes():
    allowed = allowed_numbers(_inv())
    assert {"0.003", "8.2", "6", "58"} <= allowed
```

- [ ] **Step 4: Run the test to verify it fails, then write `agent/tools/provenance.py`**

Run: `pytest agent/tests/test_provenance.py -v` → FAIL, `ModuleNotFoundError`.

```python
"""PRD 9.6: no number in the 8D that is not in a tool result.

A warning pass, not a hard gate — the investigation still finishes, but the violation is
emitted as a system event and shown in the UI so a human can see what to check.
"""
import re

from agent.models import EightD, Investigation

NUMBER = re.compile(r"\d+(?:\.\d+)?")
# Dates, section labels and ordinary prose numbers that carry no factual claim.
ALWAYS_OK = {str(n) for n in range(0, 13)} | {"2026", "16949", "2019", "8"}


def _variants(value) -> set[str]:
    text = str(value)
    out = {text}
    try:
        number = float(text)
        out |= {f"{number:g}", f"{number:.1f}", f"{number:.2f}", f"{number:.3f}",
                f"{int(number)}" if number.is_integer() else text,
                f"{number:,.0f}", f"{abs(number):g}"}
    except ValueError:
        pass
    return {v.lstrip("+") for v in out}


def allowed_numbers(inv: Investigation) -> set[str]:
    allowed: set[str] = set(ALWAYS_OK)
    for result in inv.results:
        for value in (result.p_value, result.effect_value, result.n_defect, result.n_good):
            allowed |= _variants(value)
        allowed |= set(NUMBER.findall(result.effect))
    for citation in inv.citations:
        allowed |= set(NUMBER.findall(f"{citation.label} {citation.ref} {citation.quote}"))
    for row in inv.traveler_rows:
        allowed |= set(NUMBER.findall(row.lot_id))
        for value in (row.reflow_peak_temp_c, row.time_above_liquidus_s, row.aoi_bridges):
            if value is not None:
                allowed |= _variants(value)
    allowed |= set(NUMBER.findall(inv.lot_id))
    if inv.defect:
        allowed |= _variants(round(inv.defect.confidence * 100))
    return allowed


def check_numbers(eight_d: EightD, allowed: set[str]) -> list[str]:
    violations: list[str] = []
    for name in (f"D{i}" for i in range(1, 9)):
        section = getattr(eight_d, name)
        cited = set()
        for citation in section.citations:
            cited |= set(NUMBER.findall(f"{citation.label} {citation.ref} {citation.quote}"))
        for found in NUMBER.findall(section.text):
            if found.lstrip("+") not in allowed and found not in cited:
                violations.append(f"{name}: {found} is not in any tool result")
    return violations
```

Run: `pytest agent/tests/test_provenance.py -v`
Expected: 4 passed

- [ ] **Step 5: Write the five agent modules**

Each file is one agent: its output schema, its prompt assembly, its tool calls. They publish events but do not know about HTTP.

`agent/agents/vision.py`:

```python
from agent.events import bus
from agent.models import Defect
from agent.tools.vision_tool import analyze_defect_image


async def run(inv_id: str, image_bytes: bytes, mime_type: str) -> Defect:
    await bus.publish(inv_id, "vision", "step_started", "Looking at the defect photo")
    defect = analyze_defect_image(image_bytes, mime_type)
    await bus.publish(inv_id, "vision", "tool_result",
                      f"{defect.type.replace('_', ' ').capitalize()} · "
                      f"{defect.severity.capitalize()} · {defect.confidence:.0%}",
                      detail=defect.visual_evidence, data=defect.model_dump())
    return defect
```

`agent/agents/intake.py` — publishes `step_started`, calls `parse_complaint`, publishes a `tool_result` naming customer/product/lot/quantity; if traveler bytes were uploaded, calls `parse_lot_traveler` and publishes a second `tool_result` with the row count and any `low_confidence_fields` found (this is the visible "works without an MES" moment).

`agent/agents/investigator.py` — the heart. Its LLM call returns only hypotheses; every verdict comes from `test_hypothesis`.

```python
from pydantic import BaseModel, Field

from agent.events import bus
from agent.models import Defect, Hypothesis, HypothesisResult, MemoryEntry
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.memory import search_quality_memory
from agent.tools.plant_data import get_lot_genealogy, get_maintenance_events, get_process_window
from agent.tools.stats_test import test_hypothesis


class HypothesisList(BaseModel):
    hypotheses: list[Hypothesis] = Field(min_length=3, max_length=5)


async def run(inv_id: str, lot_id: str, defect: Defect,
              traveler_note: str = "") -> tuple[list[Hypothesis], list[HypothesisResult],
                                                list[MemoryEntry]]:
    await bus.publish(inv_id, "investigator", "step_started", "Checking quality memory")
    hits = search_quality_memory(defect.type, f"{defect.type} {defect.visual_evidence}")
    for hit in hits:
        await bus.publish(inv_id, "investigator", "memory_hit",
                          f"Similar past case found: {hit.capa_id}",
                          detail=hit.root_cause, data=hit.model_dump())
    if not hits:
        await bus.publish(inv_id, "investigator", "tool_result", "No similar past case found")

    genealogy = get_lot_genealogy(lot_id)
    window = get_process_window()
    events = get_maintenance_events(genealogy["line"])
    await bus.publish(inv_id, "investigator", "tool_call",
                      f"Pulling lot genealogy and process window for {lot_id}",
                      detail=f"Line {genealogy['line']}, shift {genealogy['shift']}, "
                             f"{window['n_lots']} lots in the last {window['days']} days")

    prompt = (f"{load_prompt('investigator')}\n\n"
              f"Defect: {defect.type} ({defect.severity}). {defect.visual_evidence}\n"
              f"Affected lot: {genealogy}\n"
              f"Process window: {window}\n"
              f"Maintenance events on this line: {events}\n"
              f"Quality memory hits: {[h.model_dump() for h in hits]}\n"
              f"Shift-lead notes: {traveler_note or 'none'}\n")
    proposed = generate_structured(prompt, HypothesisList).hypotheses

    results: list[HypothesisResult] = []
    for hypothesis in proposed:
        await bus.publish(inv_id, "investigator", "hypothesis",
                          f"{hypothesis.id} {hypothesis.text}",
                          detail=f"{hypothesis.category} · "
                                 f"{hypothesis.parameter or hypothesis.event_wo_id} · "
                                 f"expected {hypothesis.direction}",
                          data=hypothesis.model_dump())
        await bus.publish(inv_id, "investigator", "tool_call",
                          f"Testing: {hypothesis.text}",
                          detail="Comparing defect lots with good lots of the same product")
        try:
            result = test_hypothesis(hypothesis.id, lot_id, parameter=hypothesis.parameter,
                                     event_wo_id=hypothesis.event_wo_id,
                                     direction=hypothesis.direction)
        except ValueError as exc:
            await bus.publish(inv_id, "investigator", "tool_result",
                              f"{hypothesis.id} could not be tested", detail=str(exc))
            continue
        results.append(result)
        await bus.publish(inv_id, "investigator", "hypothesis_result",
                          f"{hypothesis.id} {result.verdict}",
                          detail=f"{result.test}, p = {result.p_value:.4f}, {result.effect}",
                          data=result.model_dump())
    return proposed, results, hits
```

`agent/agents/evidence.py` — builds one query per supported (and, if none, per inconclusive) hypothesis from the defect type and the parameter name, calls `search_quality_docs(query, k=3)`, converts each `Passage` into a `Citation` with `label` formatted as `PFMEA row 14` / `Control plan item 6` (derived from source + ref), and publishes one `citation` event each. It always adds a synthetic `Citation(label="Chart: reflow peak temp by lot", source="chart", ref=chart_url)` when a chart exists, so the writer can cite it.

`agent/agents/writer.py`:

```python
from pydantic import BaseModel

from agent.events import bus
from agent.models import EightD, Investigation
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.provenance import allowed_numbers, check_numbers


class WriterOutput(BaseModel):
    status: str                    # "draft_ready" or "insufficient_evidence"
    eight_d: EightD | None = None
    missing_data: list[str] = []


async def run(inv_id: str, inv: Investigation) -> WriterOutput:
    supported = [r for r in inv.results if r.verdict == "supported"]
    await bus.publish(inv_id, "writer", "step_started",
                      "Drafting the 8D" if supported else "Checking whether the evidence is enough")

    prompt = (f"{load_prompt('writer')}\n\n"
              f"Complaint: {inv.complaint_id}, lot {inv.lot_id}\n"
              f"Defect: {inv.defect.model_dump() if inv.defect else None}\n"
              f"Hypotheses: {[h.model_dump() for h in inv.hypotheses]}\n"
              f"TEST RESULTS (the only source of numbers):"
              f" {[r.model_dump() for r in inv.results]}\n"
              f"Citations available: {[c.model_dump() for c in inv.citations]}\n"
              f"Lots to hold: {sorted({r.hypothesis_id for r in supported}) and inv.hold_lots}\n")
    out = generate_structured(prompt, WriterOutput, temperature=0.3)

    if out.eight_d:
        violations = check_numbers(out.eight_d, allowed_numbers(inv))
        if violations:
            await bus.publish(inv_id, "system", "error",
                              "Numbers in the draft are not backed by a tool result",
                              detail="; ".join(violations[:5]))
    await bus.publish(inv_id, "writer", "draft_ready",
                      "8D draft ready for review" if out.status == "draft_ready"
                      else "Insufficient evidence — escalate",
                      detail="; ".join(out.missing_data),
                      data={"status": out.status})
    return out
```

Add `hold_lots: list[str] = Field(default_factory=list)` to `Investigation` in `agent/models.py` — the orchestrator fills it from the defect-lot group so D3 and the hold action name the same lots.

- [ ] **Step 6: Write the failing test for the orchestrator**

`agent/tests/test_orchestrator.py` stubs the three LLM-backed steps and lets the real statistics, real plant data and real event bus run. This is the §8 golden path as an automated test.

```python
import json
from pathlib import Path

import pytest

from agent.models import Defect, EightD, EightDSection, Hypothesis
from agent import orchestrator
from agent.agents import investigator as inv_agent
from agent.agents import writer as writer_agent
from agent.events import bus
from agent.state import MemoryStateStore
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT

FX = Path(__file__).parent / "fixtures"

HYPOTHESES = [
    Hypothesis(id="H1", category="Machine", text="Stencil wear increased paste deposit",
               parameter="stencil_print_count", direction="higher"),
    Hypothesis(id="H2", category="Machine",
               text="Reflow peak temperature drifted up on Line 2 after WO-388",
               parameter="reflow_peak_temp_c", event_wo_id="WO-388", direction="higher"),
    Hypothesis(id="H3", category="Environment", text="Room humidity caused paste slump",
               parameter="room_humidity_pct", direction="higher"),
    Hypothesis(id="H4", category="Man", text="A different operator ran the defect lots",
               parameter="operator_id", direction="higher"),
]


@pytest.fixture
def wired(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr("agent.state.get_state", lambda: store)
    monkeypatch.setattr("agent.events.get_state", lambda: store)
    monkeypatch.setattr(orchestrator, "get_state", lambda: store)
    defect = Defect.model_validate(json.loads((FX / "vision_solder_bridge.json").read_text()))
    monkeypatch.setattr("agent.agents.vision.analyze_defect_image", lambda *a, **k: defect)
    monkeypatch.setattr(inv_agent, "generate_structured",
                        lambda *a, **k: inv_agent.HypothesisList(hypotheses=HYPOTHESES))
    monkeypatch.setattr(inv_agent, "search_quality_memory", lambda *a, **k: [])
    section = EightDSection(text="Verified by Welch t-test [Chart: reflow peak temp by lot].")
    monkeypatch.setattr(writer_agent, "generate_structured", lambda *a, **k:
                        writer_agent.WriterOutput(status="draft_ready",
                                                  eight_d=EightD(**{f"D{i}": section
                                                                    for i in range(1, 9)})))
    return store


@pytest.mark.asyncio
async def test_golden_path_reaches_draft_ready(wired):
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="solder bridging")
    await orchestrator.run_investigation(inv_id)
    inv = wired.get_investigation(inv_id)
    assert inv.status == "draft_ready"


@pytest.mark.asyncio
async def test_required_verdicts_hold_end_to_end(wired):
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="solder bridging")
    await orchestrator.run_investigation(inv_id)
    verdicts = {r.hypothesis_id: r.verdict for r in wired.get_investigation(inv_id).results}
    assert verdicts["H2"] == "supported"
    assert verdicts["H1"] == "rejected"
    assert verdicts["H3"] == "rejected"
    assert verdicts["H4"] == "inconclusive"


@pytest.mark.asyncio
async def test_rejected_hypotheses_stay_in_the_state(wired):
    """PRD 17: rejected cards must stay visible — the answer to 'it's theatre'."""
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="x")
    await orchestrator.run_investigation(inv_id)
    inv = wired.get_investigation(inv_id)
    assert len(inv.results) == 4
    assert sum(1 for r in inv.results if r.verdict == "rejected") == 2


@pytest.mark.asyncio
async def test_hold_lots_are_the_defect_lots(wired):
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="x")
    await orchestrator.run_investigation(inv_id)
    assert sorted(wired.get_investigation(inv_id).hold_lots) == sorted(DRIFT_LOT_IDS)


@pytest.mark.asyncio
async def test_four_actions_are_proposed(wired):
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="x")
    await orchestrator.run_investigation(inv_id)
    kinds = {a.kind for a in wired.get_investigation(inv_id).proposed_actions}
    assert kinds == {"capa", "hold", "work_order", "customer_reply"}


@pytest.mark.asyncio
async def test_a_clean_board_ends_in_insufficient_evidence(wired, monkeypatch):
    clean = Defect.model_validate(json.loads((FX / "vision_clean_board.json").read_text()))
    monkeypatch.setattr("agent.agents.vision.analyze_defect_image", lambda *a, **k: clean)
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="x")
    await orchestrator.run_investigation(inv_id)
    inv = wired.get_investigation(inv_id)
    assert inv.status == "insufficient_evidence"
    assert inv.missing_data


@pytest.mark.asyncio
async def test_the_event_stream_tells_the_whole_story(wired):
    inv_id = await orchestrator.start(complaint_id="C-2026-031", lot_id=GOLDEN_LOT,
                                      image_bytes=(FX / "tiny.jpg").read_bytes(),
                                      mime_type="image/jpeg", complaint_text="x")
    await orchestrator.run_investigation(inv_id)
    types = [e.type for e in bus.history(inv_id)]
    assert types[-1] == "done"
    assert types.count("hypothesis_result") == 4
    assert "draft_ready" in types
    assert [e.seq for e in bus.history(inv_id)] == list(range(len(types)))
```

- [ ] **Step 7: Run the test to verify it fails, then write `agent/orchestrator.py`**

Run: `pytest agent/tests/test_orchestrator.py -v` → FAIL, `ModuleNotFoundError`.

```python
"""The golden path (PRD 8), in order, emitting events as it goes."""
import logging
import uuid
from datetime import datetime, timezone

from agent.agents import evidence, intake, investigator, vision, writer
from agent.events import bus
from agent.models import Investigation, ProposedAction
from agent.state import get_state
from agent.tools.plant_data import get_comparison_groups, get_lot_genealogy

log = logging.getLogger(__name__)
_uploads: dict[str, dict] = {}        # inv_id -> raw bytes, kept out of the state store


async def start(*, complaint_id: str, lot_id: str, image_bytes: bytes, mime_type: str,
                complaint_text: str, traveler_bytes: bytes | None = None) -> str:
    inv_id = f"inv_{uuid.uuid4().hex[:8]}"
    _uploads[inv_id] = {"image": image_bytes, "mime": mime_type,
                        "complaint_text": complaint_text, "traveler": traveler_bytes}
    inv = Investigation(id=inv_id, complaint_id=complaint_id, lot_id=lot_id, status="running",
                        created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    get_state().save_investigation(inv)
    await bus.publish(inv_id, "system", "step_started", "Investigation started",
                      detail=f"Complaint {complaint_id} · lot {lot_id}")
    return inv_id


def _propose_actions(inv: Investigation) -> list[ProposedAction]:
    line = get_lot_genealogy(inv.lot_id)["line"]
    cause = next((h.text for h in inv.hypotheses
                  if h.id in {r.hypothesis_id for r in inv.results if r.verdict == "supported"}),
                 "confirmed root cause")
    return [
        ProposedAction(id="A1", kind="capa",
                       summary=f"Corrective action for {inv.defect.type.replace('_', ' ')} "
                               f"on {inv.lot_id}",
                       payload={"cause": cause, "lot_id": inv.lot_id, "line": line}),
        ProposedAction(id="A2", kind="hold",
                       summary=f"Hold {len(inv.hold_lots)} lots: "
                               f"{inv.hold_lots[0]}–{inv.hold_lots[-1]}"
                               if inv.hold_lots else "Hold suspect lots",
                       payload={"lots": inv.hold_lots}),
        ProposedAction(id="A3", kind="work_order",
                       summary=f"Verify and re-qualify reflow profile on Line {line[-1]}",
                       payload={"line": line, "asset": "Reflow oven",
                                "description": f"Verify and re-qualify reflow profile {line}"}),
        ProposedAction(id="A4", kind="customer_reply",
                       summary="Draft reply to the customer in Japanese and English",
                       payload={}),
    ]


async def run_investigation(inv_id: str) -> None:
    state = get_state()
    inv = state.get_investigation(inv_id)
    upload = _uploads.get(inv_id, {})
    try:
        complaint, traveler_rows = await intake.run(
            inv_id, upload.get("complaint_text", ""), inv.complaint_id,
            upload.get("traveler"))
        inv.traveler_rows = traveler_rows
        state.save_investigation(inv)

        inv.defect = await vision.run(inv_id, upload["image"], upload.get("mime", "image/jpeg"))
        state.save_investigation(inv)

        if inv.defect.type == "none":
            inv.status = "insufficient_evidence"
            inv.missing_data = [
                "No defect is visible in the photo. Upload a clearer image of the "
                "reported area, or escalate to a physical inspection of the returned units."]
            state.save_investigation(inv)
            await bus.publish(inv_id, "writer", "draft_ready",
                              "Insufficient evidence — escalate",
                              detail=inv.missing_data[0],
                              data={"status": "insufficient_evidence"})
            return

        note = " | ".join(r.remarks for r in traveler_rows if r.remarks)
        inv.hypotheses, inv.results, inv.memory_hits = await investigator.run(
            inv_id, inv.lot_id, inv.defect, note)
        inv.hold_lots = get_comparison_groups(inv.lot_id)["defect_lots"]
        inv.chart_url = next((r.chart_url for r in inv.results if r.chart_url), None)
        state.save_investigation(inv)

        inv.citations = await evidence.run(inv_id, inv)
        state.save_investigation(inv)

        out = await writer.run(inv_id, inv)
        inv.eight_d = out.eight_d
        inv.missing_data = out.missing_data
        inv.status = "draft_ready" if out.status == "draft_ready" else "insufficient_evidence"
        if inv.status == "draft_ready":
            inv.proposed_actions = _propose_actions(inv)
        state.save_investigation(inv)
    except Exception as exc:
        log.exception("investigation %s failed", inv_id)
        await bus.publish(inv_id, "system", "error", "The investigation could not finish",
                          detail=f"{exc.__class__.__name__}: {exc}")
        raise
    finally:
        _uploads.pop(inv_id, None)
        await bus.publish(inv_id, "system", "done", "Investigation complete")
        bus.close(inv_id)
```

Run: `pytest agent/tests/test_orchestrator.py -v`
Expected: 7 passed

- [ ] **Step 8: Decide the ADK question explicitly**

PRD §3 requires Google ADK. The orchestration above is a plain async pipeline, which is what makes it testable. Wrap it rather than rewrite it: define each of the five steps as an ADK `LlmAgent` with its tools registered, compose them with `SequentialAgent`, and have each agent's callback publish the same events.

```bash
python -c "import google.adk, inspect; print(google.adk.__version__); \
import google.adk.agents as a; print([n for n in dir(a) if n.endswith('Agent')])"
```

Build the wrapper in `agent/agents/root.py` against whatever that prints. If the installed ADK surface differs from what the docs describe, follow the current docs — PRD §9 explicitly allows this, and the agent boundaries, tools and events stay identical either way. Record in `README.md` which ADK classes were used.

- [ ] **Step 9: Commit**

```bash
git add agent/events.py agent/orchestrator.py agent/agents agent/tools/provenance.py agent/tests
git commit -m "feat: agent pipeline, event bus and number-provenance check

Golden path test asserts H2 supported, H1/H3 rejected, H4 inconclusive end to end."
```

---

### Task 10: The API — seven endpoints and the SSE stream

**Files:**
- Create: `prototype/backend/agent/main.py`
- Create: `prototype/backend/agent/tests/test_api_contract.py`

**Interfaces:**
- Consumes: `agent.orchestrator.start` / `run_investigation`, `agent.events.bus`, `agent.state.get_state`, `agent.tools.intake_tools.list_complaints`, `agent.tools.memory.list_quality_memory`, `agent.tools.storage.get_local_path`, `agent.config.get_settings`.
- Exact signature `agent.agents.intake.run` must expose (the orchestrator already calls it this way): `async def run(inv_id: str, complaint_text: str, complaint_id: str, traveler_bytes: bytes | None) -> tuple[Complaint, list[TravelerRow]]`.
- Produces: the seven PRD §12 endpoints plus `GET /api/files/{key:path}` for locally stored charts and photos. Task 12's `frontend/src/api/client.ts` is written against exactly these.

- [ ] **Step 1: Write the failing contract test**

`agent/tests/test_api_contract.py` — asserts the field names and status values the UI depends on, so backend and UI cannot drift apart silently.

```python
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FX = Path(__file__).parent / "fixtures"
# tests -> agent -> backend -> prototype, so docs/contract is three levels up.
CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "contract"


@pytest.fixture
def client(monkeypatch):
    from agent import main
    monkeypatch.setattr(main, "run_investigation", lambda inv_id: None)
    return TestClient(main.app)


def test_health_reports_the_model_from_env(client, monkeypatch):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert "model" in body


def test_complaints_carry_the_inbox_fields(client):
    rows = client.get("/api/complaints").json()
    golden = next(c for c in rows if c["complaint_id"] == "C-2026-031")
    assert golden["customer"] == "Hoshino Denso (fictional)"
    assert golden["product"] == "ECU-PCB-7"
    assert golden["lot_id"] == "L2611"
    assert "due_in_working_days" in golden


def test_creating_an_investigation_returns_id_and_running(client):
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "solder bridging"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"].startswith("inv_")
    assert body["status"] == "running"


def test_creating_without_an_image_is_rejected(client):
    resp = client.post("/api/investigations",
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "x"})
    assert resp.status_code == 422


def test_unknown_investigation_is_404(client):
    assert client.get("/api/investigations/inv_nope").status_code == 404


def test_mock_investigation_matches_the_response_model():
    """The file Susan builds against must deserialise as a real Investigation."""
    from agent.models import Investigation
    inv = Investigation.model_validate(json.loads((CONTRACT / "mock_investigation.json").read_text()))
    assert inv.status in ("running", "draft_ready", "approved", "insufficient_evidence")
    assert inv.eight_d is not None
    assert {a.kind for a in inv.proposed_actions} == {"capa", "hold", "work_order", "customer_reply"}


def test_mock_events_match_the_event_model():
    from agent.models import Event
    events = [Event.model_validate(e)
              for e in json.loads((CONTRACT / "mock_events.json").read_text())]
    assert [e.seq for e in events] == list(range(len(events)))
    assert events[-1].type == "done"
    assert any(e.type == "hypothesis_result" and e.data["verdict"] == "supported" for e in events)
    assert sum(1 for e in events
               if e.type == "hypothesis_result" and e.data["verdict"] == "rejected") == 2


def test_sse_stream_is_an_event_stream(client, monkeypatch):
    from agent import main
    resp = client.post("/api/investigations",
                       files={"image": ("tiny.jpg", (FX / "tiny.jpg").read_bytes(), "image/jpeg")},
                       data={"complaint_id": "C-2026-031", "lot_id": "L2611",
                             "complaint_text": "x"})
    inv_id = resp.json()["id"]
    with client.stream("GET", f"/api/investigations/{inv_id}/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        first = next(stream.iter_lines())
        assert first.startswith("data: ")


def test_memory_endpoint_returns_a_list(client):
    assert isinstance(client.get("/api/memory").json(), list)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest agent/tests/test_api_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.main'`

- [ ] **Step 3: Write `agent/main.py`**

```python
"""FastAPI surface. docs/contract/README.md is the agreement — change both sides together."""
import asyncio
import json
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent.config import get_settings
from agent.events import bus
from agent.orchestrator import run_investigation, start
from agent.state import get_state
from agent.tools.intake_tools import list_complaints
from agent.tools.memory import list_quality_memory
from agent.tools.storage import get_local_path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="8D Copilot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


class ApproveRequest(BaseModel):
    approver: str = "Priya R."
    edits: dict[str, str] = {}
    rejected_action_ids: list[str] = []
    note: str = ""


@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "model": s.gemini_model,
            "backends": {"plant": s.plant_backend, "state": s.state_backend,
                         "docs": s.docs_backend, "files": s.files_backend}}


@app.get("/api/complaints")
def complaints():
    return [c.model_dump() for c in list_complaints()]


@app.post("/api/investigations")
async def create_investigation(
        image: UploadFile = File(...),
        complaint_id: str = Form(""),
        complaint_text: str = Form(""),
        lot_id: str = Form(...),
        traveler: UploadFile | None = File(None)):
    inv_id = await start(
        complaint_id=complaint_id, lot_id=lot_id,
        image_bytes=await image.read(), mime_type=image.content_type or "image/jpeg",
        complaint_text=complaint_text,
        traveler_bytes=await traveler.read() if traveler else None)
    asyncio.create_task(_run(inv_id))
    return {"id": inv_id, "status": "running"}


async def _run(inv_id: str):
    try:
        await run_investigation(inv_id)
    except Exception:
        log.exception("background investigation %s failed", inv_id)


@app.get("/api/investigations/{inv_id}/events")
async def stream_events(inv_id: str):
    async def generator():
        try:
            async for event in bus.subscribe(inv_id):
                yield f"data: {json.dumps(event.model_dump())}\n\n"
        except asyncio.CancelledError:        # client navigated away
            return

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no",
                                      "Connection": "keep-alive"})


@app.get("/api/investigations/{inv_id}")
def get_investigation(inv_id: str):
    inv = get_state().get_investigation(inv_id)
    if inv is None:
        raise HTTPException(404, f"no investigation {inv_id}")
    return inv.model_dump()


@app.post("/api/investigations/{inv_id}/approve")
async def approve(inv_id: str, body: ApproveRequest):
    from agent.agents.actions import apply_approval
    inv = get_state().get_investigation(inv_id)
    if inv is None:
        raise HTTPException(404, f"no investigation {inv_id}")
    if inv.status != "draft_ready":
        raise HTTPException(409, f"investigation is {inv.status}, not draft_ready")
    return await apply_approval(inv, approver=body.approver, edits=body.edits,
                                rejected_action_ids=body.rejected_action_ids, note=body.note)


@app.get("/api/memory")
def memory():
    return [m.model_dump() for m in list_quality_memory()]


@app.get("/api/files/{key:path}")
def files(key: str):
    path = get_local_path(key)
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest agent/tests/test_api_contract.py -v`
Expected: 9 passed

If `test_mock_investigation_matches_the_response_model` fails, fix the mock JSON written in Task 0 — not the model. The mock exists to be exactly what the API returns.

- [ ] **Step 5: Run the server and walk the golden path by hand**

```bash
uvicorn agent.main:app --reload --port 8000 &
curl -s localhost:8000/api/health | python -m json.tool
curl -s localhost:8000/api/complaints | python -m json.tool | head -30

INV=$(curl -s -X POST localhost:8000/api/investigations \
  -F image=@data/images/defect_01.jpg \
  -F complaint_id=C-2026-031 -F lot_id=L2611 \
  -F "complaint_text=Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units." \
  -F traveler=@data/out/lot_traveler_line2_wk41.xlsx | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "investigation $INV"
curl -N -s localhost:8000/api/investigations/$INV/events | head -40
curl -s localhost:8000/api/investigations/$INV | python -m json.tool | head -60
```

**Phase 4 gate (PRD §15):** the golden path runs locally, H2 is supported, H1 and H3 rejected, H4 inconclusive, and the 8D draft carries citations. Time the run — PRD §13 allows 90 s.

- [ ] **Step 6: Commit**

```bash
git add agent/main.py agent/tests/test_api_contract.py
git commit -m "feat: FastAPI endpoints and SSE event stream"
```

---

### Task 11: Approval, actions and the bilingual reply

**Files:**
- Create: `prototype/backend/agent/agents/actions.py`
- Create: `prototype/backend/agent/tests/test_actions.py`

**Interfaces:**
- Consumes: `agent.state.get_state`, `agent.tools.memory.save_quality_memory`, `agent.tools.llm.generate_structured`, `agent.models`.
- Produces: `apply_approval(inv, *, approver, edits, rejected_action_ids, note) -> dict` returning exactly the PRD §12.5 shape: `{"capa_id", "hold_id", "work_order_id", "replies": {"ja", "en"}, "memory_id"}`, with `None` for any action the approver switched off.

- [ ] **Step 1: Write the failing test**

`agent/tests/test_actions.py`:

```python
import pytest

from agent.agents import actions
from agent.models import (Citation, Defect, EightD, EightDSection, Hypothesis,
                          HypothesisResult, Investigation, ProposedAction)
from agent.state import MemoryStateStore


def _inv() -> Investigation:
    section = EightDSection(text="Original text [PFMEA row 14].",
                            citations=[Citation(label="PFMEA row 14", source="pfmea.md",
                                                ref="Row 14")])
    return Investigation(
        id="inv_1", complaint_id="C-2026-031", lot_id="L2611", status="draft_ready",
        defect=Defect(type="solder_bridge", severity="major", box=[0.1, 0.1, 0.2, 0.2],
                      confidence=0.86, visual_evidence="Bridge between two pads."),
        hypotheses=[Hypothesis(id="H2", category="Machine",
                               text="Reflow peak temperature drift on Line 2 after WO-388",
                               parameter="reflow_peak_temp_c", direction="higher")],
        results=[HypothesisResult(hypothesis_id="H2", verdict="supported", test="Welch t-test",
                                  p_value=0.003, effect="+8.2 °C", effect_value=8.2,
                                  effect_unit="°C", n_defect=6, n_good=58)],
        hold_lots=["L2609", "L2610", "L2611", "L2612", "L2613", "L2614"],
        eight_d=EightD(**{f"D{i}": section for i in range(1, 9)}),
        proposed_actions=[
            ProposedAction(id="A1", kind="capa", summary="CAPA"),
            ProposedAction(id="A2", kind="hold", summary="Hold",
                           payload={"lots": ["L2609", "L2610", "L2611",
                                             "L2612", "L2613", "L2614"]}),
            ProposedAction(id="A3", kind="work_order", summary="WO",
                           payload={"line": "L2", "asset": "Reflow oven",
                                    "description": "Verify and re-qualify reflow profile"}),
            ProposedAction(id="A4", kind="customer_reply", summary="Reply"),
        ])


@pytest.fixture
def store(monkeypatch):
    s = MemoryStateStore()
    monkeypatch.setattr(actions, "get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.embed", lambda texts: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(actions, "generate_structured", lambda *a, **k: actions.Replies(
        ja="いつもお世話になっております。", en="Thank you for your continued support."))
    return s


@pytest.mark.asyncio
async def test_all_four_actions_create_records(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert out["capa_id"].startswith("CAPA-")
    assert out["hold_id"].startswith("H-")
    assert out["work_order_id"].startswith("WO-")
    assert out["memory_id"].startswith("MEM-")
    assert out["replies"]["ja"] and out["replies"]["en"]


@pytest.mark.asyncio
async def test_a_rejected_action_is_not_created(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=["A3"], note="")
    assert out["work_order_id"] is None
    assert out["capa_id"] is not None


@pytest.mark.asyncio
async def test_edits_are_applied_and_attributed(store):
    inv = _inv()
    await actions.apply_approval(inv, approver="Priya R.",
                                 edits={"D4": "Edited by the engineer."},
                                 rejected_action_ids=[], note="checked on the line")
    saved = store.get_investigation("inv_1")
    assert saved.eight_d.D4.text == "Edited by the engineer."
    assert saved.eight_d.D1.text == "Original text [PFMEA row 14]."
    assert saved.status == "approved"
    assert saved.approver == "Priya R."


@pytest.mark.asyncio
async def test_hold_names_every_suspect_lot(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert store.get_record("hold", out["hold_id"])["lots"] == [
        "L2609", "L2610", "L2611", "L2612", "L2613", "L2614"]


@pytest.mark.asyncio
async def test_memory_stores_the_confirmed_cause_only(store):
    await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                 rejected_action_ids=[], note="")
    entries = store.list_memory()
    assert len(entries) == 1
    assert "Reflow peak temperature drift" in entries[0].root_cause
    assert entries[0].defect_type == "solder_bridge"


@pytest.mark.asyncio
async def test_approving_twice_is_rejected(store):
    inv = _inv()
    await actions.apply_approval(inv, approver="Priya R.", edits={},
                                 rejected_action_ids=[], note="")
    with pytest.raises(ValueError, match="already approved"):
        await actions.apply_approval(store.get_investigation("inv_1"), approver="Priya R.",
                                     edits={}, rejected_action_ids=[], note="")
```

- [ ] **Step 2: Run the test to verify it fails, then write `agent/agents/actions.py`**

Run: `pytest agent/tests/test_actions.py -v` → FAIL, `ModuleNotFoundError`.

```python
"""What happens after a human approves. Records are created by plain code;
exactly one LLM call writes the bilingual reply (PRD 9.2)."""
from datetime import date

from pydantic import BaseModel

from agent.events import bus
from agent.models import Investigation
from agent.state import get_state
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.memory import save_quality_memory


class Replies(BaseModel):
    ja: str
    en: str


def _confirmed_cause(inv: Investigation) -> str:
    supported = {r.hypothesis_id for r in inv.results if r.verdict == "supported"}
    for hypothesis in inv.hypotheses:
        if hypothesis.id in supported:
            return hypothesis.text
    return ""


async def apply_approval(inv: Investigation, *, approver: str, edits: dict[str, str],
                         rejected_action_ids: list[str], note: str) -> dict:
    if inv.status == "approved":
        raise ValueError(f"investigation {inv.id} is already approved")

    state = get_state()
    for section_name, new_text in edits.items():
        if inv.eight_d and hasattr(inv.eight_d, section_name):
            getattr(inv.eight_d, section_name).text = new_text

    accepted = {a.id: a for a in inv.proposed_actions if a.id not in rejected_action_ids}
    cause = _confirmed_cause(inv)
    line = next((a.payload.get("line", "") for a in accepted.values()
                 if a.kind == "work_order"), "")
    out: dict = {"capa_id": None, "hold_id": None, "work_order_id": None,
                 "replies": None, "memory_id": None}

    for action in accepted.values():
        if action.kind == "capa":
            out["capa_id"] = state.create_record("capa", {
                "investigation_id": inv.id, "complaint_id": inv.complaint_id,
                "lot_id": inv.lot_id, "root_cause": cause, "owner": "Quality Manager",
                "opened": date.today().isoformat(), "status": "open",
                "summary": action.summary, "approver": approver, "note": note})
        elif action.kind == "hold":
            out["hold_id"] = state.create_record("hold", {
                "investigation_id": inv.id, "lots": action.payload.get("lots", inv.hold_lots),
                "reason": cause, "raised": date.today().isoformat(), "status": "active"})
        elif action.kind == "work_order":
            out["work_order_id"] = state.create_record("work_order", {
                "investigation_id": inv.id, "line": action.payload.get("line", ""),
                "asset": action.payload.get("asset", ""),
                "description": action.payload.get("description", ""),
                "raised": date.today().isoformat(), "status": "open",
                "requested_by": approver})

    if "A4" in accepted or any(a.kind == "customer_reply" for a in accepted.values()):
        prompt = (f"{load_prompt('customer_reply')}\n\n"
                  f"Customer complaint: {inv.complaint_id}, lot {inv.lot_id}\n"
                  f"Defect: {inv.defect.type if inv.defect else ''}\n"
                  f"Confirmed root cause: {cause}\n"
                  f"Lots contained: {', '.join(inv.hold_lots)}\n"
                  f"CAPA number: {out['capa_id']}\n"
                  f"Permanent action: {inv.eight_d.D5.text if inv.eight_d else ''}\n")
        replies = generate_structured(prompt, Replies, temperature=0.3)
        out["replies"] = replies.model_dump()

    if cause:
        out["memory_id"] = save_quality_memory(
            investigation_id=inv.id,
            defect_type=inv.defect.type if inv.defect else "other",
            root_cause=cause,
            parameter=next((h.parameter or "" for h in inv.hypotheses
                            if h.id in {r.hypothesis_id for r in inv.results
                                        if r.verdict == "supported"}), ""),
            line=line, capa_id=out["capa_id"] or "", lot_id=inv.lot_id)

    inv.status = "approved"
    inv.approver = approver
    state.save_investigation(inv)
    await bus.publish(inv.id, "system", "done", f"8D approved by {approver}",
                      detail=note, data={k: v for k, v in out.items() if k != "replies"})
    return out
```

Run: `pytest agent/tests/test_actions.py -v`
Expected: 6 passed

- [ ] **Step 3: Verify the Japanese reply reads as business keigo**

```bash
INV=... # id from Task 10 step 5
curl -s -X POST localhost:8000/api/investigations/$INV/approve \
  -H 'content-type: application/json' \
  -d '{"approver":"Priya R.","edits":{},"rejected_action_ids":[],"note":"verified on the line"}' \
  | python -m json.tool
```

Read the `ja` field. It must open with a standard business greeting, use polite forms throughout, and name the CAPA number. If it reads as literal translation rather than keigo, tighten `agent/prompts/customer_reply.md` with a worked example of the opening and closing lines. Have someone who reads Japanese check it before the video is recorded.

- [ ] **Step 4: Prove the memory loop with the second lot**

PRD §8.8 — this is the moment that separates the product from an 8D generator.

```bash
curl -s -X POST localhost:8000/api/investigations \
  -F image=@data/images/defect_02.jpg -F complaint_id=C-2026-031 -F lot_id=L2613 \
  -F "complaint_text=Solder bridging reported on lot 2613." \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])"
# then stream the events and look for type == "memory_hit"
```

Expected: a `memory_hit` event naming the CAPA created in Step 3, and the reflow hypothesis tested first. If no hit appears, lower `MIN_SIMILARITY` in `agent/tools/memory.py` only after checking the stored `root_cause` text actually resembles the new query.

- [ ] **Step 5: Commit**

```bash
git add agent/agents/actions.py agent/tests/test_actions.py
git commit -m "feat: approval creates CAPA, hold, work order, bilingual reply and memory"
```

---

### Task 12: The web app on mocks — six screens

Build against `docs/contract/*.json` with `VITE_USE_MOCKS=true`, so screens progress without waiting for the backend.

**Files:**
- Create: `prototype/frontend/` (Vite scaffold), `frontend/tailwind.config.js`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/api/types.ts`, `client.ts`, `mocks.ts`, `useInvestigationStream.ts`
- Create: `frontend/src/components/AppShell.tsx`, `VerdictPill.tsx`, `Timeline.tsx`, `HypothesisCard.tsx`, `DefectPhoto.tsx`, `CitationChip.tsx`, `CitationSheet.tsx`, `EightDSection.tsx`, `ActionToggle.tsx`, `TempChart.tsx`
- Create: `frontend/src/pages/Inbox.tsx`, `NewInvestigation.tsx`, `LiveInvestigation.tsx`, `Evidence.tsx`, `Review.tsx`, `Done.tsx`, `Memory.tsx`

**Interfaces:**
- Consumes: the Task 10 endpoints; `docs/contract/mock_events.json` and `mock_investigation.json` when `VITE_USE_MOCKS=true`.
- Produces:
  - `api/types.ts` — TypeScript mirrors of every Pydantic model (`Complaint`, `Defect`, `Hypothesis`, `HypothesisResult`, `Citation`, `EightD`, `ProposedAction`, `Investigation`, `MemoryEntry`, `AgentEvent`)
  - `api/client.ts` — `listComplaints()`, `createInvestigation(form)`, `getInvestigation(id)`, `approve(id, body)`, `listMemory()`
  - `useInvestigationStream(id)` → `{ events, defect, hypotheses, results, citations, status, memoryHits, chartUrl }`

- [ ] **Step 1: Scaffold and install**

```bash
cd "/Users/a2862717/Documents/AI Builder Cup/prototype"
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install react-router-dom chart.js react-chartjs-2
npm install -D tailwindcss @tailwindcss/postcss postcss autoprefixer
```

Configure Tailwind per its current setup instructions for Vite, then put the §13 palette in `src/index.css` as CSS variables so every component draws from one place:

```css
:root {
  --ink: #16211c;        /* body text */
  --paper: #fbfcfb;      /* page background */
  --card: #ffffff;
  --line: #e2e8e4;
  --green: #1b5e3f;      /* deep green accent, supported */
  --grey: #6b7670;       /* rejected */
  --amber: #b7791f;      /* warnings, inconclusive — warnings only, per PRD 13 */
  --red: #a6281f;
}
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8efea; --paper: #0f1512; --card: #161d19; --line: #27312c; }
}
body { background: var(--paper); color: var(--ink); font-family: ui-sans-serif, system-ui, sans-serif; }
.mono { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-variant-numeric: tabular-nums; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

- [ ] **Step 2: Write `src/api/types.ts` and `client.ts`**

Mirror the Pydantic models field-for-field — the contract test in Task 10 guards the Python side, these types guard the TypeScript side.

```ts
export type Verdict = "supported" | "rejected" | "inconclusive";
export type Status = "running" | "draft_ready" | "approved" | "insufficient_evidence";

export interface Defect {
  type: string; severity: string; box: [number, number, number, number];
  confidence: number; visual_evidence: string;
}
export interface HypothesisResult {
  hypothesis_id: string; verdict: Verdict; test: string; p_value: number;
  effect: string; effect_value: number; effect_unit: string;
  n_defect: number; n_good: number; group_labels: string[]; chart_url: string | null;
}
export interface AgentEvent {
  seq: number; ts: string;
  agent: "intake" | "vision" | "investigator" | "evidence" | "writer" | "system";
  type: "step_started" | "tool_call" | "tool_result" | "memory_hit" | "hypothesis"
      | "hypothesis_result" | "citation" | "draft_ready" | "done" | "error";
  title: string; detail: string; data: Record<string, unknown>;
}
// ...Complaint, Hypothesis, Citation, EightD, ProposedAction, Investigation, MemoryEntry
```

```ts
const BASE = import.meta.env.VITE_API_URL ?? "";
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return res.json() as Promise<T>;
}

export const listComplaints = () =>
  USE_MOCKS ? mockComplaints() : json<Complaint[]>("/complaints");

export const getInvestigation = (id: string) =>
  USE_MOCKS ? mockInvestigation() : json<Investigation>(`/investigations/${id}`);

export const createInvestigation = async (form: FormData) =>
  USE_MOCKS ? { id: "inv_mock", status: "running" as const }
            : json<{ id: string; status: Status }>("/investigations",
                { method: "POST", body: form });

export const approve = (id: string, body: ApproveBody) =>
  USE_MOCKS ? mockApproval() : json<ApproveResult>(`/investigations/${id}/approve`,
    { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(body) });
```

- [ ] **Step 3: Write `src/api/useInvestigationStream.ts`**

One hook owns the live trace. In mock mode it replays `mock_events.json` one event every 600 ms, exactly as PRD §12 asks.

```ts
import { useEffect, useRef, useState } from "react";
import mockEvents from "@contract/mock_events.json";   // alias set in vite.config.ts
import { AgentEvent, Citation, Defect, HypothesisResult, Status, USE_MOCKS } from "./types";

export function useInvestigationStream(id: string | undefined) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const seen = useRef(new Set<number>());

  useEffect(() => {
    if (!id) return;
    seen.current.clear();
    setEvents([]);

    const push = (e: AgentEvent) => {
      if (seen.current.has(e.seq)) return;      // SSE reconnect replays history
      seen.current.add(e.seq);
      setEvents(prev => [...prev, e].sort((a, b) => a.seq - b.seq));
    };

    if (USE_MOCKS) {
      let i = 0;
      const timer = setInterval(() => {
        if (i >= (mockEvents as AgentEvent[]).length) { clearInterval(timer); return; }
        push((mockEvents as AgentEvent[])[i++]);
      }, 600);
      return () => clearInterval(timer);
    }

    const source = new EventSource(
      `${import.meta.env.VITE_API_URL ?? ""}/api/investigations/${id}/events`);
    source.onmessage = (m) => {
      const event = JSON.parse(m.data) as AgentEvent;
      push(event);
      if (event.type === "done" || event.type === "error") source.close();
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [id]);

  const by = <T,>(type: string) => events.filter(e => e.type === type).map(e => e.data as T);
  const defect = (events.find(e => e.agent === "vision" && e.type === "tool_result")
                  ?.data as Defect | undefined) ?? null;
  const results = by<HypothesisResult>("hypothesis_result");
  const draft = events.find(e => e.type === "draft_ready");

  return {
    events, defect, results,
    hypotheses: by<Hypothesis>("hypothesis"),
    citations: by<Citation>("citation"),
    memoryHits: by<MemoryEntry>("memory_hit"),
    chartUrl: results.find(r => r.chart_url)?.chart_url ?? null,
    status: (draft?.data?.status as Status | undefined)
            ?? (events.some(e => e.type === "error") ? "running" : "running"),
    done: events.some(e => e.type === "done"),
  };
}
```

- [ ] **Step 4: Write `AppShell.tsx` and `VerdictPill.tsx`**

`AppShell` carries the §7 header and footer on every screen, the bottom tab bar below 768 px and the sidebar above it.

```tsx
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col">
      <header className="flex items-center gap-3 px-4 h-14 border-b"
              style={{ borderColor: "var(--line)" }}>
        <Logo className="h-6 w-auto" />
        <span className="text-sm opacity-70 truncate">Sree Electronics (fictional), Chennai</span>
        <span className="ml-auto flex items-center gap-2 text-sm">
          <span className="grid place-items-center h-8 w-8 rounded-full text-white text-xs"
                style={{ background: "var(--green)" }} aria-hidden>PR</span>
          <span className="hidden sm:inline">Priya R. · Quality Engineer</span>
        </span>
      </header>
      <main className="flex-1 px-4 py-4 max-w-[1280px] w-full mx-auto">{children}</main>
      <footer className="px-4 py-3 text-xs opacity-60 border-t"
              style={{ borderColor: "var(--line)" }}>
        Synthetic demo data · Built with Gemini on Google Cloud
      </footer>
      <TabBar className="md:hidden" />
    </div>
  );
}
```

`VerdictPill` must carry text, not colour alone (§13 accessibility):

```tsx
const STYLE: Record<Verdict, { bg: string; label: string }> = {
  supported:    { bg: "var(--green)", label: "Supported" },
  rejected:     { bg: "var(--grey)",  label: "Rejected" },
  inconclusive: { bg: "var(--amber)", label: "Inconclusive" },
};

export function VerdictPill({ verdict }: { verdict: Verdict }) {
  const s = STYLE[verdict];
  return (
    <span className="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium text-white"
          style={{ background: s.bg }}>
      {s.label}
    </span>
  );
}
```

- [ ] **Step 5: Build the six screens against the mocks**

Each screen is PRD §7. Build in this order so the demo path is walkable first.

**`Inbox.tsx` (`/`)** — one card per open complaint: customer, product, lot, defect, and `8D due in N working days` with the countdown amber when `due_in_working_days <= 3`. A "Past investigations" list below, and a link to `/memory`. Tapping a card goes to `/new?complaint=C-2026-031`.

**`NewInvestigation.tsx` (`/new`)** — `<input type="file" accept="image/*" capture="environment">` for the camera on phones, complaint text prefilled from the query parameter, lot field prefilled, an optional second file input for the traveler `.xlsx`, and a "Start investigation" button that POSTs the `FormData` and navigates to `/inv/:id`.

**`LiveInvestigation.tsx` (`/inv/:id`)** — `DefectPhoto` draws the bounding box as a positioned `div` using the 0–1 fractions, with the chip `Solder bridge · Major · 86%`. `Timeline` lists every event with agent, title and time. `HypothesisCard` per result: the hypothesis text, a `VerdictPill`, and `p = 0.0031` in `.mono`. **Rejected cards stay on screen** — never filter them. A `memory_hit` event renders a "Similar past case found" row above the cards. When `status === "draft_ready"`, show a "Review 8D" button to `/inv/:id/review`.

**`Evidence.tsx` (`/inv/:id/evidence`)** — the chart from `chart_url` as an `<img>` with alt text describing what it shows, a per-hypothesis stats table (test, p, effect, group sizes, all `.mono`), and `CitationChip`s that open `CitationSheet` with the quote and `source · ref`.

**`Review.tsx` (`/inv/:id/review`)** — D1–D8 as collapsible sections with auto-growing `<textarea>`s, citation chips inline, the four actions as toggles, an optional note field, and "Approve 8D". When `status === "insufficient_evidence"`, show the banner with `missing_data` and **hide the Approve button**.

**`Done.tsx` (`/inv/:id/done`)** — `8D approved by Priya R.`, cards for the CAPA, hold (naming every lot) and work order, the customer reply card defaulting to Japanese with an English toggle and a Copy button, and a "Saved to quality memory" card showing the confirmed cause.

**`Memory.tsx` (`/memory`)** — the saved confirmed causes from `GET /memory`.

- [ ] **Step 6: Check the two viewport widths and the a11y rules**

```bash
npm run dev
```

In the browser's device toolbar at 390 px and 1280 px, confirm for every screen: no horizontal scroll, every button at least 44 px tall, visible focus rings on tab, images have alt text, and verdict pills still readable in greyscale (use the rendering emulation "grayscale" filter — the labels must carry the meaning).

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat: six screens built against the mock contract"
```

---

### Task 13: Wire the web app to the live API

**Files:**
- Modify: `frontend/.env.local` (gitignored), `frontend/src/api/client.ts` if any field mismatch appears
- Create: `prototype/frontend/README.md`

- [ ] **Step 1: Point the app at the running backend**

```bash
cd prototype/frontend
printf 'VITE_API_URL=http://localhost:8000\nVITE_USE_MOCKS=false\n' > .env.local
npm run dev
```

- [ ] **Step 2: Walk the golden path in the browser at 390 px**

Inbox → C-2026-031 → upload `data/images/defect_01.jpg` and `data/out/lot_traveler_line2_wk41.xlsx` → Start. Watch for, in order: the defect box and chip inside 10 s; four hypothesis cards with two rejected still visible; the chart on Evidence; D1–D8 with citation chips; edit D4; switch off one action; Approve; the done screen with the Japanese reply.

**Phase 5 gate (PRD §15):** the full flow runs in a phone-sized window against the real local API.

- [ ] **Step 3: Fix what the live data exposes**

Mocks hide three things that only appear live: an SSE reconnect replaying events (the `seen` set in the hook handles it — verify by throttling the network), a `chart_url` that is a relative `/api/files/...` path (prefix it with `VITE_API_URL` in `DefectPhoto`/`Evidence`), and a `draft_ready` that arrives before `GET /investigations/{id}` has the 8D (refetch on the `draft_ready` event rather than on mount only).

- [ ] **Step 4: Run the no-defect edge case**

Upload `data/images/no_defect_01.jpg`. Expect the `insufficient_evidence` banner with the missing-data text and no Approve button. This is PRD §8.9 and it is worth ten seconds in the video.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: web app running against the live API"
```

---

### Task 14: Move the data to Google Cloud

Independent of Tasks 5–13 once Task 2 has written the documents — run it in parallel if a second person is available.

**Files:**
- Create: `prototype/backend/infra/load_data.sh`
- Modify: `prototype/.env` (local, gitignored) — the backend reads it from `backend/` via `env_file="../.env"` in `config.py`

- [ ] **Step 1: Create the project and enable the services**

Per PRD §11.1:

```bash
gcloud auth login
gcloud projects create 8d-copilot-2026 --name="8D Copilot"
gcloud config set project 8d-copilot-2026
gcloud billing projects link 8d-copilot-2026 --billing-account=<ACCOUNT_ID>
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com \
  firestore.googleapis.com storage.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com firebase.googleapis.com
gcloud auth application-default login
```

Set a budget alert on the billing account before the first model call — PRD §17 lists trial limits as a named risk.

- [ ] **Step 2: Pick the models and record them**

```bash
export GCP_PROJECT=8d-copilot-2026 GCP_REGION=asia-south1
python -m infra.probe_models
```

Put the chosen Gemini Flash and embedding IDs into `.env` as `GEMINI_MODEL` and `EMBED_MODEL`, with `VERTEX_REGION` set to the region they are served from. Write both IDs and the region into `README.md`.

- [ ] **Step 3: Write and run `infra/load_data.sh`**

```bash
#!/usr/bin/env bash
# Loads the synthetic plant into BigQuery and the assets into Cloud Storage.
set -euo pipefail
: "${GCP_PROJECT:?}" "${GCP_REGION:?}" "${BQ_DATASET:?}" "${GCS_BUCKET:?}"
OUT="$(dirname "$0")/../data/out"

bq --location="$GCP_REGION" mk --dataset --force "$GCP_PROJECT:$BQ_DATASET"
for table in lots process maintenance complaints; do
  bq load --replace --autodetect --source_format=CSV --skip_leading_rows=1 \
     "$GCP_PROJECT:$BQ_DATASET.$table" "$OUT/$table.csv"
  echo "loaded $table"
done

gcloud storage buckets create "gs://$GCS_BUCKET" --location="$GCP_REGION" 2>/dev/null || true
gcloud storage cp "$(dirname "$0")/../data/images"/* "gs://$GCS_BUCKET/images/"
gcloud storage cp "$(dirname "$0")/../data/docs"/*  "gs://$GCS_BUCKET/docs/"
gcloud storage cp "$OUT/lot_traveler_line2_wk41.xlsx" "gs://$GCS_BUCKET/docs/"

bq query --use_legacy_sql=false \
  "SELECT line, COUNT(*) lots, ROUND(AVG(p.reflow_peak_temp_c),1) avg_peak
   FROM \`$GCP_PROJECT.$BQ_DATASET.lots\` l
   JOIN \`$GCP_PROJECT.$BQ_DATASET.process\` p USING (lot_id)
   GROUP BY line ORDER BY line"
```

```bash
chmod +x infra/load_data.sh && ./infra/load_data.sh
```

Expected: two rows, with Line L2's average peak visibly higher than L1's.

- [ ] **Step 4: Create the Firestore database and the vector index**

```bash
gcloud firestore databases create --location="$GCP_REGION" --type=firestore-native
```

Then the composite vector index from Task 7 Step 3, using the dimension `EMBED_MODEL` actually returns.

- [ ] **Step 5: Build the RAG corpus**

```bash
python -m infra.build_rag
```

**Phase 2 gate (PRD §15):** the test query returns PFMEA row 14 with its source. Copy the printed corpus name into `.env` as `RAG_CORPUS`.

- [ ] **Step 6: Flip every backend to cloud and rerun the golden path**

```bash
sed -i '' 's/^PLANT_BACKEND=.*/PLANT_BACKEND=bigquery/;s/^STATE_BACKEND=.*/STATE_BACKEND=firestore/;s/^DOCS_BACKEND=.*/DOCS_BACKEND=vertex/;s/^FILES_BACKEND=.*/FILES_BACKEND=gcs/' .env
pytest agent/tests -v -k "not test_plant_data and not test_doc_search"
uvicorn agent.main:app --port 8000
```

Walk the browser golden path again. The CSV-backed unit tests are excluded because they assert against local files by design; everything else must pass unchanged. If a cloud backend misbehaves during the demo window, flip that one variable back — that is what the selector is for.

- [ ] **Step 7: Add the team to IAM**

```bash
for member in user:<susan> user:<vishwaa>; do
  for role in roles/aiplatform.user roles/bigquery.dataEditor roles/bigquery.jobUser \
              roles/storage.objectAdmin roles/datastore.user roles/run.developer \
              roles/firebasehosting.admin; do
    gcloud projects add-iam-policy-binding 8d-copilot-2026 --member="$member" --role="$role"
  done
done
```

- [ ] **Step 8: Commit**

```bash
git add infra/load_data.sh README.md
git commit -m "feat: load synthetic plant into BigQuery, GCS and the RAG corpus"
```

---

### Task 15: Hardening — seven cases, replay mode, README

**Files:**
- Create: `prototype/backend/infra/run_cases.py`
- Create: `prototype/backend/agent/replay.py`
- Modify: `prototype/backend/agent/main.py` (replay branch), `prototype/README.md`

**Interfaces:**
- Produces: `agent.replay.record(inv_id, case_name)` writing `data/out/replay/<case>.json`, and `agent.replay.replay(case_name, inv_id)` republishing those events on the bus at their original spacing. `main.py` checks `settings.replay_case` in `create_investigation` and replays instead of calling models.

- [ ] **Step 1: Write `infra/run_cases.py`**

PRD §15 Phase 7 gate: at least 6 of 7 cases pass.

```python
"""Runs the seven demo cases end to end and prints a pass table.
Usage: python -m infra.run_cases   (needs the API running on :8000)
"""
import json
import sys
import time
from pathlib import Path

import httpx

API = "http://localhost:8000/api"
IMAGES = Path(__file__).resolve().parents[1] / "data" / "images"
TRAVELER = Path(__file__).resolve().parents[1] / "data" / "out" / "lot_traveler_line2_wk41.xlsx"

CASES = [
    # name,            lot,     image,              expect_status,            expect
    ("golden L2611",   "L2611", "defect_01.jpg", "draft_ready",
     {"supported": {"reflow_peak_temp_c"}, "min_rejected": 1}),
    ("drift L2612",    "L2612", "defect_02.jpg", "draft_ready",
     {"supported": {"reflow_peak_temp_c"}, "min_rejected": 1}),
    ("drift L2614",    "L2614", "defect_03.jpg", "draft_ready",
     {"supported": {"reflow_peak_temp_c"}, "min_rejected": 1}),
    ("good L2590",     "L2590", "defect_04.jpg", "any", {"min_rejected": 1}),
    ("good L2601",     "L2601", "defect_05.jpg", "any", {"min_rejected": 1}),
    ("line 1 L2605",   "L2605", "defect_01.jpg", "any", {"min_rejected": 1}),
    ("no defect",      "L2611", "no_defect_01.jpg", "insufficient_evidence", {}),
]


def run_case(name, lot, image, expect_status, expect) -> tuple[bool, str]:
    files = {"image": (image, (IMAGES / image).read_bytes(), "image/jpeg")}
    data = {"complaint_id": "C-2026-031", "lot_id": lot,
            "complaint_text": f"Solder bridging reported on lot {lot[1:]}."}
    if lot != "L2611":
        files["traveler"] = (TRAVELER.name, TRAVELER.read_bytes(),
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    inv_id = httpx.post(f"{API}/investigations", files=files, data=data, timeout=60).json()["id"]

    deadline = time.time() + 180
    inv = {}
    while time.time() < deadline:
        inv = httpx.get(f"{API}/investigations/{inv_id}", timeout=30).json()
        if inv["status"] != "running":
            break
        time.sleep(2)
    else:
        return False, "timed out after 180 s"

    if expect_status != "any" and inv["status"] != expect_status:
        return False, f"status {inv['status']}, expected {expect_status}"

    results = inv.get("results", [])
    hypotheses = {h["id"]: h for h in inv.get("hypotheses", [])}
    supported_params = {hypotheses.get(r["hypothesis_id"], {}).get("parameter")
                        for r in results if r["verdict"] == "supported"}
    rejected = sum(1 for r in results if r["verdict"] == "rejected")

    if "supported" in expect and not (expect["supported"] & supported_params):
        return False, f"expected {expect['supported']} supported, got {supported_params}"
    if rejected < expect.get("min_rejected", 0):
        return False, f"only {rejected} rejected hypotheses — judges need to see one"
    if inv["status"] == "draft_ready" and not inv.get("eight_d"):
        return False, "draft_ready without an 8D"
    return True, f"{len(results)} hypotheses, {rejected} rejected, status {inv['status']}"


passed = 0
print(f"{'case':18}{'result':8}detail")
for case in CASES:
    ok, detail = run_case(*case)
    passed += ok
    print(f"{case[0]:18}{'PASS' if ok else 'FAIL':8}{detail}")

print(f"\n{passed}/{len(CASES)} cases passed (gate: 6)")
Path("data/out/run_cases.json").write_text(json.dumps(
    {"passed": passed, "total": len(CASES)}, indent=2))
sys.exit(0 if passed >= 6 else 1)
```

```bash
python -m infra.run_cases
```

Expected: at least 6 of 7 PASS. A failing "good lot" case usually means the investigator proposed nothing testable for a lot with no defect signal — that is acceptable as long as `min_rejected` is met; tighten the investigator prompt rather than the gate.

- [ ] **Step 2: Write `agent/replay.py`**

PRD §13 reliability: a recorded run that plays back if the network fails during recording.

```python
"""Replay a recorded run. Live mode is the default; REPLAY_CASE switches it on."""
import asyncio
import json
from pathlib import Path

from agent.events import bus
from agent.models import Event, Investigation
from agent.state import get_state

DIR = Path(__file__).resolve().parents[1] / "data" / "out" / "replay"


def record(inv_id: str, case_name: str) -> Path:
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{case_name}.json"
    inv = get_state().get_investigation(inv_id)
    path.write_text(json.dumps({
        "investigation": inv.model_dump(),
        "events": [e.model_dump() for e in bus.history(inv_id)]}, indent=2))
    return path


async def replay(case_name: str, inv_id: str, gap: float = 0.6) -> None:
    payload = json.loads((DIR / f"{case_name}.json").read_text())
    inv = Investigation.model_validate(payload["investigation"])
    inv.id = inv_id
    for raw in payload["events"]:
        event = Event.model_validate(raw)
        await bus.publish(inv_id, event.agent, event.type, event.title,
                          detail=event.detail, data=event.data)
        await asyncio.sleep(gap)
    get_state().save_investigation(inv)
    bus.close(inv_id)
```

In `agent/main.py`, inside `create_investigation`, before `asyncio.create_task(_run(inv_id))`:

```python
    if get_settings().replay_case:
        asyncio.create_task(replay(get_settings().replay_case, inv_id))
        return {"id": inv_id, "status": "running"}
```

Record the golden run and prove the replay:

```bash
python -c "
from agent.replay import record; print(record('<inv_id from the golden run>', 'golden'))"
REPLAY_CASE=golden uvicorn agent.main:app --port 8000
```

Walk the browser flow with the network to Google Cloud switched off. Every screen must still fill. Put a visible `Replay mode` chip in the header when `GET /api/health` reports a non-empty `replay_case`, so a judge is never misled about what they are watching.

- [ ] **Step 3: Write `prototype/README.md`**

Sections, in this order:

1. **What it does** — the §1 one-liner and the tagline.
2. **The demo in 60 seconds** — the §8 golden path as numbered steps with a screenshot each.
3. **Architecture** — the §11 diagram, and a sentence on why statistics and not the model decide verdicts.
4. **How to run** — toolchain, `pip install -e ".[dev]"`, `python -m data.generate_plant`, `python -m data.check_plant`, `./infra/load_data.sh`, `python -m infra.build_rag`, `uvicorn agent.main:app`, `npm run dev`. Include the `.env` table with every variable and the backend selectors.
5. **What is synthetic** — all plant data, all four quality documents, both company names. The planted root cause and its decoys, stated openly. The exact command (`python -m data.check_plant`) a judge can run to see the decoys get rejected.
6. **Models and region** — the `GEMINI_MODEL` and `EMBED_MODEL` IDs actually used and the region, with the note that they are read from the environment and never hard-coded.
7. **Credits** — VisA dataset (Amazon Science, CC BY 4.0); the ALLPCB and AIM Solder references from §18 that shaped the value ranges.
8. **Tests** — `pytest agent/tests -v` and `python -m infra.run_cases`, with the current pass counts.
9. **Known issues and cut lines** — anything from the cut list that was actually cut.

- [ ] **Step 4: Confirm no secret has ever been committed**

```bash
git log --all --full-history --name-only | sort -u | grep -E '^\.env$|\.json$' | head
grep -rInE '(AIza[0-9A-Za-z_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|"private_key")' \
  --exclude-dir=node_modules --exclude-dir=.git . || echo "no secrets found"
git check-ignore -v .env
```

Expected: `.env` never appears in history, the grep finds nothing, and `git check-ignore` confirms `.env` is ignored.

- [ ] **Step 5: Full test sweep and commit**

```bash
pytest agent/tests -v
python -m data.check_plant
python -m infra.run_cases
git add infra/run_cases.py agent/replay.py agent/main.py README.md
git commit -m "feat: seven-case harness, replay mode and README"
```

---

### Task 16: Deploy and submit (weekend)

**Files:**
- Create: `prototype/backend/Dockerfile`, `prototype/backend/.dockerignore`, `prototype/firebase.json`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY agent ./agent
COPY data ./data
RUN pip install --no-cache-dir -e .
EXPOSE 8080
CMD ["sh", "-c", "uvicorn agent.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 300"]
```

`backend/.dockerignore`: `.venv/`, `data/out/`, `**/__pycache__/`, `agent/tests/`. The build context is `backend/`, so `frontend/` is outside it already.

The container must still find the CSVs if a backend is flipped back, so keep `data/out/` out of the image but ensure `PLANT_BACKEND=bigquery` in the deployed service.

- [ ] **Step 2: Deploy to Cloud Run**

PRD §11: `min-instances 1` so the first demo request is not cold, `timeout 300` for the SSE stream.

```bash
cd prototype/backend
gcloud run deploy api --source . \
  --region "$GCP_REGION" --allow-unauthenticated \
  --min-instances 1 --timeout 300 --memory 2Gi --cpu 2 \
  --set-env-vars "GCP_PROJECT=$GCP_PROJECT,GCP_REGION=$GCP_REGION,VERTEX_REGION=$VERTEX_REGION,GEMINI_MODEL=$GEMINI_MODEL,EMBED_MODEL=$EMBED_MODEL,BQ_DATASET=plant,GCS_BUCKET=$GCS_BUCKET,RAG_CORPUS=$RAG_CORPUS,PLANT_BACKEND=bigquery,STATE_BACKEND=firestore,DOCS_BACKEND=vertex,FILES_BACKEND=gcs"
curl -s "$(gcloud run services describe api --region "$GCP_REGION" --format='value(status.url)')/api/health"
```

Grant the service account the same roles the local user has (`aiplatform.user`, `bigquery.dataViewer` + `jobUser`, `datastore.user`, `storage.objectAdmin`).

- [ ] **Step 3: Host the web app on Firebase with the API rewrite**

```json
{
  "hosting": {
    "public": "frontend/dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      { "source": "/api/**", "run": { "serviceId": "api", "region": "asia-south1" } },
      { "source": "**", "destination": "/index.html" }
    ]
  }
}
```

```bash
cd prototype/frontend && printf 'VITE_API_URL=\nVITE_USE_MOCKS=false\n' > .env.production \
  && npm run build && cd ..
firebase deploy --only hosting      # run from prototype/, where firebase.json lives
```

`VITE_API_URL` is empty on purpose — the rewrite puts the API on the same origin, which also removes the CORS problem. Test the SSE stream specifically: Firebase Hosting rewrites buffer some responses, and if the trace arrives in one burst rather than streaming, point the frontend at the Cloud Run URL directly and set CORS to that origin instead.

- [ ] **Step 4: Add the demo access code**

A single shared code (`DEMO_ACCESS_CODE`) checked by a FastAPI dependency on every `/api/*` route except `/api/health`, and a one-field gate screen in the web app that stores it in `sessionStorage` and sends it as an `X-Demo-Code` header. Keep `/api/health` open so judges can see the service is alive.

- [ ] **Step 5: Public repo, video, deck**

```bash
gh repo create 8d-copilot --public --source=. --remote=origin --push
```

Before pushing: re-run the secret scan from Task 15 Step 4, and confirm `README.md` names the synthetic data on its first screen.

- **Video (under 3 minutes)** — follow the §8 beats: complaint arrives → photo → the live trace with H1 visibly rejected and H2 supported → the chart → the 8D with citations → edit and approve → CAPA, hold, work order, Japanese reply → the lot-2613 memory hit. Say "the AI proposes, the data decides, a human approves" out loud, and say the data is synthetic on screen.
- **PDF deck** — vision, problem (§4 in the plant manager's voice), benefit (§16 metrics), feasibility (§11 architecture), scalability, and one slide stating exactly what is synthetic.
- **Submission** — fill the Hack2skill form with the repo, the hosted URL, the access code, the video and the deck.

- [ ] **Step 6: Final commit and tag**

```bash
git add infra/Dockerfile firebase.json .dockerignore README.md
git commit -m "chore: Cloud Run and Firebase Hosting deployment"
git tag v1.0 && git push --tags
```

---

## Verification Summary

Run these in order. Every one must pass before the prototype is called done.

| Gate | Command | Expected |
|---|---|---|
| Data (Phase 1) | `python -m data.check_plant` | exit 0; H2 supported, H1/H3/H5 rejected, H4 inconclusive, defect lots == L2609–L2614 |
| Tools (Phase 3) | `pytest agent/tests -v` | all pass, no cloud needed for the CSV-backed modules |
| RAG (Phase 2) | `python -m infra.build_rag` | test query returns PFMEA row 14 with its source |
| Agents + API (Phase 4) | `pytest agent/tests/test_orchestrator.py agent/tests/test_api_contract.py -v` | golden path reaches `draft_ready` with the four required verdicts |
| UI (Phase 5) | manual walk at 390 px | full flow, no horizontal scroll, defect box < 10 s |
| Memory (Phase 6) | lot L2613 run | `memory_hit` event naming the CAPA from the first run |
| Hardening (Phase 7) | `python -m infra.run_cases` | ≥ 6 of 7 |
| Secrets | the Task 15 Step 4 scan | nothing found, `.env` ignored |

---

## Self-Review

**Spec coverage.** Walked PRD §§1–18. Every section maps to a task: §7's six screens → Task 12; §9.2's seven agents → Tasks 5–9 and 11; §9.3's statistics tool → Task 4; §9.4's five prompts → Task 5; §10's data spec → Tasks 1–2; §11's stack → Tasks 3, 7, 14; §12's seven endpoints → Task 10; §13's non-functionals → Tasks 12, 13, 15; §15's eight phases → the gate table above.

Three PRD items are deliberately handled differently, each flagged where it happens:
- §10.5 says "PDF (or Markdown if PDF is slow)" — Task 2 writes Markdown, because heading-based chunking gives exact `Row 14` citation refs that a PDF extractor would have to guess at.
- §11.3's repo layout nests `data/docs` and `docs/contract` as written; the plan keeps both and adds `data/constants.py`, which the PRD does not name but which is what stops the generator and the stats tool from disagreeing.
- §9.2 lists `get_comparison_groups` and `get_process_window` as investigator tools; they are implemented in Task 3 and called by Task 9's investigator, which is the same thing one layer down.

**Placeholder scan.** No "TBD", no "add error handling", no "similar to Task N". Two steps intentionally describe rather than dictate — Task 9 Step 8 (the ADK wrapper, because the installed API surface must be read first, which PRD §9's preamble explicitly permits) and Task 12 Step 5 (the six screens, specified by content, data source and acceptance rather than full JSX). Both state what "done" means.

**Type consistency.** Checked across tasks: `classify(p_value, effect, direction, min_effect)` is defined in Task 1 and called identically in Tasks 4 and 1's `check_plant.py`. `test_hypothesis(hypothesis_id, lot_id, parameter, event_wo_id, direction)` is defined in Task 4 and called with those keywords in Task 9. `HypothesisResult` field names match between `models.py` (Task 0), `stats_test.py` (Task 4), `mock_events.json` (Task 0) and `types.ts` (Task 12). `apply_approval` returns the exact five keys Task 10's `/approve` passes through and Task 11's tests assert.

One fix applied inline during review: Task 9's `writer.py` references `inv.hold_lots`, which `models.py` as written in Task 0 does not define — Task 9 Step 5 now carries the explicit instruction to add `hold_lots: list[str]` to `Investigation`.

---

## Open Questions

Neither blocks a single task; both are worth settling before Sunday.

1. **Submission deadline.** PRD §3 records that the team's working date is Sun 18 Oct while the official FAQ only confirms team formation closing 14 Oct. Confirm the real deadline on the Hack2skill portal — it decides how much of Task 16 happens Saturday rather than Sunday.
2. **Schedule reality.** The Team Playbook put Friday 16 Oct as feature freeze and video day; this plan starts the build on Friday. Tasks 0–13 are the local prototype and Tasks 14–16 the deployment, so the cut lines in "Task Order and Cut Lines" are the lever if Saturday gets tight.
