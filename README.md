# 8D Copilot

A quality-engineering agent for an SMT electronics plant. A photo and a customer complaint
go in; a statistically tested root cause and a cited 8D report come out.

**"The AI proposes, the data decides, a human approves."**

A quality engineer photographs a defective circuit board and pastes the customer
complaint. The system identifies the defect, proposes root causes, tests each one against
factory data with real statistics, drafts a fully cited 8D report, and — after a human
approves — creates the corrective action, lot hold, work order, a Japanese and English
customer reply, and saves the confirmed cause to quality memory.

Built for the Google Cloud AI Builder Cup 2026, manufacturing theme. All plant, customer
and defect data is synthetic; see [What is synthetic](#what-is-synthetic).

## The demo in 60 seconds

1. The inbox shows complaint **C-2026-031** from Hoshino Denso (fictional): solder
   bridging on ECU-PCB-7, lot L2611, 14 of 500 units, 8D due in 10 working days.
2. The engineer opens it, uploads the defect photo and the messy Line 2 lot-traveler
   spreadsheet, and starts the investigation.
3. Vision identifies the defect: solder bridge, major, with a bounding box on the photo.
4. The investigator proposes five hypotheses across the 6Ms and tests each one against
   plant data:
   - **Supported** — reflow peak temperature drift on Line 2 after work order WO-388
     (+7.2 °C, p < 0.01)
   - **Rejected** — stencil wear (a new stencil means fewer prints, the wrong direction)
   - **Rejected** — room humidity
   - **Rejected** — paste age
   - **Inconclusive** — operator change (confounded in time with the maintenance event)
5. The evidence page shows the reflow-temperature chart, the per-hypothesis statistics,
   and citations: PFMEA row 14, control plan item 6, and a past 8D.
6. The engineer edits the drafted 8D and approves it.
7. The system creates CAPA-0142, lot hold H-77 (L2609–L2614), work order WO-412, a
   bilingual customer reply, and a quality-memory entry for the confirmed cause.
8. Starting a second investigation on lot L2613 retrieves the first case from memory by
   meaning, not by keyword, before any hypothesis is tested.

## What is synthetic

All plant data, all four quality documents, and both company names ("Sree Electronics
(fictional), Chennai" and "Hoshino Denso (fictional)") are synthetic. The defect photos
are real, but they are stock images from a public anomaly-detection dataset, not photos
of this fictional plant's hardware — see [Credits](#credits).

The root cause is **planted on purpose**: `backend/data/generate_plant.py` builds a
64-lot, 30-day dataset in which Line 2's reflow peak temperature drifts upward after a
real maintenance event (WO-388, oven heater replaced, profile verification never signed
off) and three decoy causes are built in to fail for specific, checkable reasons — a new
stencil that should reduce wear, not increase it; humidity that is uniform noise; an
operator whose start date overlaps the real event too closely to separate from it.

A sceptical judge can watch this happen directly:

```bash
cd backend && python -m data.check_plant
```

This prints a verdict table and asserts every required verdict against the same
classifier the live agent uses, so the data gate and the product can never disagree. A
real run against the generated dataset:

```
id   hypothesis                              test              p          effect  verdict      required
H2   Reflow peak temp drift (L2, WO-388)     Welch t      0.0004        +7.2 °C   supported    supported
H2b  Time above liquidus                     Welch t      0.0001       +21.0 s    supported    supported
H1   Stencil wear (print count)              Welch t      0.0000    -29614.7 prints rejected     rejected
H3   Room humidity                           Welch t      0.9780        +0.1 %RH  rejected     rejected
H5   Paste age                               Welch t      0.4704        -2.1 h    rejected     rejected
H4   Operator change (OP-17)                 Fisher       0.0177       +0.49 share inconclusive inconclusive

All required verdicts and invariants hold. Dataset is demo-ready.
```

Owning this is stronger than burying it: the interesting claim is not that a cause was
found, it's that the same statistical test that confirms it also correctly rejects three
plausible-looking decoys.

## Architecture

```
React (Vite + TypeScript) + SSE
        │
FastAPI + Google ADK agents (Python 3.12)
   │          │            │            │
   ▼          ▼            ▼            ▼
Gemini    BigQuery     Firestore   Cloud Storage
(Vertex   (plant       (investiga- (photos,
 AI)       data)        tions,      docs,
                        CAPA,       charts)
                        holds,
                        memory)
   │
   ▼
Vertex AI RAG Engine (PFMEA, control plan, past 8Ds)
```

One agent per pipeline stage — intake, vision, investigator, evidence, writer, and a
post-approval actions step — each publishing events over an SSE stream the UI renders
live. Every stage that calls Gemini uses structured output validated with Pydantic.

**Deterministic statistics, not the model, decide every verdict.** `backend/agent/tools/
stats_test.py` runs a Welch t-test (numeric parameters) or a Fisher exact test
(categorical parameters, e.g. operator) and a direction-aware classifier
(`stats_verdict.classify`) turns the p-value and effect size into `supported` /
`rejected` / `inconclusive`; the model only proposes which parameter to test and reads
the verdict back. `CLAUDE.md`'s golden rule states this as a hard rule: the LLM never
writes a p-value, a measurement or a verdict, and `agent/tools/stats_test.py` is the
only module allowed to produce one. A second pass, `agent/tools/provenance.py`,
checks every number in the drafted 8D against the set of numbers that actually appeared
in a tool result, and flags anything that isn't.

The app runs against local files (`PLANT_BACKEND=csv`, `STATE_BACKEND=memory`,
`DOCS_BACKEND=local`, `FILES_BACKEND=local`) or against Google Cloud
(`PLANT_BACKEND=bigquery`, `STATE_BACKEND=firestore`, `DOCS_BACKEND=vertex`,
`FILES_BACKEND=gcs`) with no code change — `GET /api/health`'s `backends` object reports
which is active.

## How to run

From a clean clone:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m data.generate_plant      # writes backend/data/out/ — synthetic plant data, docs, images
python -m data.check_plant         # asserts the planted cause and the three decoys classify correctly
uvicorn agent.main:app --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

`.env.example` (repo root) carries **local** defaults — `PLANT_BACKEND=csv`,
`STATE_BACKEND=memory`, `DOCS_BACKEND=local`, `FILES_BACKEND=local` — so a fresh clone
runs fully offline with no Google Cloud project. Flipping each backend to
`bigquery` / `firestore` / `vertex` / `gcs` switches that one concern to Google Cloud;
`GCP_PROJECT`, `GCP_REGION`, `BQ_DATASET`, `GCS_BUCKET`, `RAG_CORPUS` and `FIRESTORE_DB`
configure the cloud side once any backend is flipped.

## Replay mode

`REPLAY_CASE=golden` streams a previously recorded investigation back over the same SSE
endpoint with no model calls at all — spacing comes from the recorded timestamps rather
than a fixed interval, so a replayed run looks like it is thinking, not looping. It
exists because Vertex's quota returned 429 on the vision call repeatedly during
development; a demo should not depend on a quota window holding. Replay never hides
itself: `GET /api/health` reports `"replay": "golden"` and the UI shows a `Replay` chip
in the header, so a viewer is never unsure whether a run is live.

## Models and region

- `GEMINI_MODEL=gemini-2.5-flash`
- `EMBED_MODEL=text-embedding-005`
- Region: `asia-south1`

Both model names are read only from `GEMINI_MODEL` and `EMBED_MODEL` — never hard-coded.
A test (`backend/agent/tests/test_llm.py::test_no_model_id_is_hard_coded_anywhere_in_the_package`)
scans every `.py` and `.md` file under `backend/` for a literal `gemini-*` or
`text-embedding-*` string and fails the build if it finds one — which is why the two
model names above are named here, in the repo-root README, and nowhere under `backend/`.

## Tests

```bash
cd backend && pytest agent/tests     # 200 passing
cd frontend && npm test              # 11 passing
```

## Limitations

- **No collinearity check.** The hypothesis tester has no notion of confounding — a
  variable perfectly collinear with the true cause would be reported `supported` with
  full confidence. This is why `stencil_id` (categorical stencil identity) is
  deliberately excluded from the testable parameters: Line 2's stencil was replaced one
  day before the oven work that actually caused the drift, so every drift lot carries
  both, and a bare categorical test on stencil identity cannot tell the two apart. Stencil
  *wear* (`stencil_print_count`) is tested instead, and correctly rejects — a new stencil
  means fewer prints, not more, the wrong direction for the hypothesis.
- **The number-provenance pass is a warning, not a gate**, and it grants a blanket pass to
  every integer 0–12 (plus a few fixed literals like the year and the IATF standard
  number) so that ordinary prose numbers don't trigger false alarms. A small invented
  number in that range could slip through undetected.
- **The categorical test (Fisher exact, used for the operator hypothesis) picks the most
  common level among defect lots and compares its share to the good-lot base rate, but
  does not normalise or correct for how rare that operator is overall** beyond that
  direct comparison — it is a single two-way contingency table, not a model that controls
  for other factors.
- **The approval lock is per-process.** `apply_approval` serialises concurrent approvals
  of the same investigation with an in-memory `asyncio.Lock`, which is airtight on one
  uvicorn process but would not hold across multiple Cloud Run instances — a Firestore
  conditional write (`set status=approved only if still draft_ready`) would be the real
  fix there. This project deploys with `min-instances=1`, so the process-local lock is
  proportionate for now, not a long-term answer.
- **`defect_01.jpg` and `defect_02.jpg` are vision false negatives.** Both carry genuine,
  documented anomalies but consistently read as `none` under the final vision prompt,
  across two independent rounds of prompt tightening. Only `defect_03.jpg` reliably reads
  as a solder bridge and is used as the golden-path image.
- **Vision reads are majority-stable, not deterministic.** `defect_03.jpg` returned
  `solder_bridge` in 2 of 3 live calls (1 read `none`); the clean board (`no_defect_01.jpg`)
  returned `none` in 3 of 4 calls (1 read `misalignment`). Vision latency has ranged from
  4.4 s to 22.5 s against a 10 s target for the first visible result.
- **Lot L2611's own peak temperature (248.7 °C) is below the 250 °C profile limit**, while
  5 of the 6 lots in the affected window (L2609–L2614) exceed it. This is why the 8D
  states the root cause at the window level — the process drifted after WO-388 — rather
  than claiming the one named lot itself crossed the limit.
- **A hypothesis test is scoped to the product and a 30-day window, never to the lot under
  investigation.** `get_comparison_groups(lot_id, ...)` accepts a `lot_id` but does not
  filter on it — the defect-lots/good-lots split comes entirely from `product` and the
  trailing 30 days. Running the harness against lots clearly outside the drifted window
  (L2590, 1 Oct; L2601, 7 Oct) still returned a **supported** reflow-temperature hypothesis,
  because a real drift exists in that window for *some* lots and the test does not check
  whether the investigated lot is one of them — only whether the photographed defect type
  warrants running the test at all. We think this is defensible, not a bug: the proposed
  hold list (`hold_lots`) is built from the actual defect lots, not from the investigated
  one, so the system never recommends containing a lot that isn't implicated, and a
  genuine process drift is a true, actionable fact about every lot made during that window
  regardless of which lot's complaint surfaced it — lot-level defect counts are noisy at
  this volume, and a multi-lot drift is the more reliable signal. But it does mean the 8D's
  root-cause finding answers "is a known process issue active right now," not "did this
  specific lot's own data show it" — those are different questions, and the draft does not
  currently flag when the investigated lot falls outside the implicated group. Read the
  window dates and `hold_lots` alongside D4 before treating a supported verdict as proof
  about the named lot itself.

## Credits

- Defect images: **VisA (Visual Anomaly) dataset**, Amazon Science (Zou et al., ECCV
  2022), CC BY 4.0. See `backend/data/images/IMAGES.md` for the exact subset, source
  files and per-image provenance.
- Process value ranges: ALLPCB's "Troubleshooting Reflow Soldering Defects" guide and
  AIM Solder's "SMT Troubleshooting Guide".
- No real company logos are used. The plant ("Sree Electronics (fictional), Chennai")
  and both customers ("Hoshino Denso (fictional)", "Kaveri Motors (fictional)") are
  fictional.
