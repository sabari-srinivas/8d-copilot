# 8D Copilot — Product Requirements Document (PRD)

**Event:** Google Cloud AI Builder Cup 2026 · Manufacturing theme · JAPAC (run by Hack2skill)
**Team:** Sabari Srinivas (development) · Susan Subramani (UI) · Vishwaa (deployment)
**Version:** 1.0 · 16 Oct 2026
**Build tool:** Claude Code (codebase), Google AI Studio (prompt testing), Google Stitch (screen designs, optional)
**Today's goal:** a working prototype running locally against real Google Cloud services. Deployment (Cloud Run + Firebase Hosting) follows on Sat/Sun.

> **For Claude Code:** read this whole file before writing code. Build in the phase order in section 15. Anything marked **MUST** is an acceptance criterion. When a Google SDK or API has changed since this was written, check the current docs and follow them, but keep the behaviour described here.

---

## 1. One-line summary

A quality engineer photographs a defective circuit board and pastes the customer complaint. 8D Copilot identifies the defect, proposes root causes, **tests each one against factory data with real statistics**, drafts a fully cited 8D report, and, after a human approves, creates the corrective action, lot hold, work order, a Japanese + English customer reply, and saves the confirmed cause to quality memory.

**Tagline (use in UI, video and deck):** *"The AI proposes, the data decides, a human approves."*

---

## 2. Hackathon context

### 2.1 What we are building for
We are building this prototype as our entry for the **Google Cloud AI Builder Cup 2026**, a JAPAC hackathon run by Hack2skill and sponsored by Google Cloud. It is open to working professionals and startups. The prize pool is USD 30,000, and shortlisted teams go to a Grand Finale in Singapore. Prize categories mentioned in our research include Best Use of Google Cloud AI Tools, Most Impactful Solution and Best UI/UX.

### 2.2 The six themes

| # | Theme | Focus |
|---|---|---|
| 1 | BFSI: Intelligent Risk, Fraud & Financial Experiences | Fraud and risk, process automation, customer interactions, personalised finance |
| 2 | Retail & Commerce: Intelligent Customer and Business Experiences | Discovery, personalisation, conversational shopping, demand planning, inventory, fraud |
| 3 | **Manufacturing: Intelligent Operations & Industrial Efficiency** ← **our theme** | Efficiency, quality, reliability, supply and demand, or sustainability, by turning operational data into insights, recommendations or actions |
| 4 | Media, Content & Digital Experiences | Creating, discovering, personalising and experiencing content |
| 5 | Future of Work & Enterprise Productivity | Knowledge access, collaboration, decisions, daily work, with measurable productivity gains |
| 6 | Sustainability & Social Impact | Resource efficiency, accessibility, resilience, community support |

### 2.3 Why we chose Manufacturing
- **The theme asks for action, not chat.** It explicitly asks to turn "operational data into insights, recommendations, or actions". That suits an agent that ends in real records (CAPA, lot hold, work order), and it avoids the chatbot cliché.
- **JAPAC relevance is strong.** India and ASEAN are absorbing supply moving from China, and Japanese and Korean OEMs expect supplier quality documents they will accept. Tier-2 and Tier-3 suppliers feel this pressure most and have the least software.
- **The data makes the AI meaningful.** Photos, complaints, messy Excel sheets, process readings and quality documents give Gemini multimodal, reasoning, retrieval and writing work in one flow. That is what the 40% technical criterion rewards.
- **We can make credible data.** Public PCB defect images (VisA) and well-documented solder-process parameters let us build a realistic synthetic plant.

### 2.4 How we chose the challenge
We ran three deep-research reports (Gemini, ChatGPT, Claude), then scored seven candidate problems on the official judging weights (`Stage2_Judge_Panel_Scoring.md`, `AI_Builder_Cup_Challenge_Cards.pdf`):

| Rank | Challenge | Theme area | Score /100 |
|---|---|---|---|
| **1** | **8D Copilot: defect photo → tested root cause → cited 8D → approved CAPA** | Quality | **85.0** |
| 2 | ShiftLoss: shift voice notes → true machine-efficiency (OEE) losses | Efficiency | 78.8 |
| 3 | Fault Memory: diagnose a machine fault, fix it, remember it | Reliability | 77.4 |
| 4 | Right Revision at the machine (drawing-change check) | Quality | 72.4 |
| 5 | Cert Check at the dock (material certificate vs spec) | Supply | 61.8 |
| 6 | Early Warning for late parts (supplier emails) | Supply | 56.4 |
| 7 | Carbon Answer for small exporters | Sustainability | 55.6 |

**Why 8D Copilot won:**
- It combines three distinct Gen AI capabilities in one flow: seeing the defect, proposing causes that statistics then test, and writing a cited document. It also uses retrieval and memory. That is the strongest fit for the 40% criterion.
- It ends in real actions, matching the theme's wording.
- It has the strongest 3-minute demo moment: a wrong cause is visibly rejected, the real one is confirmed, and a chart shows why.
- It stayed first under any single-score change in our sensitivity check.

**Its weak points, which we design against:** 8D generators already exist; the planted cause can look staged; and "works without an MES" has to be shown. Our answers are statistics-decided verdicts, visible rejected causes, the messy-Excel input and quality memory (section 17).

**Backup:** ShiftLoss, if the hypothesis-testing loop doesn't work honestly.

### 2.5 Evaluation criteria (official)

| Criterion | Weight | What judges look for | How 8D Copilot earns it |
|---|---|---|---|
| Technical Merit & Gen AI Implementation | **40%** | Meaningful use of Gen AI, technical soundness, scalability and sustainability | Multi-agent ADK flow; Gemini vision, function calling, RAG with citations, grounded writing, embeddings; statistics as the referee; Cloud Run + BigQuery + Firestore |
| Problem Alignment & Impact | **25%** | Fit to the chosen theme; value to intended users | Turns operational data into a decision and real actions; days of 8D work become minutes; fewer rejected 8Ds and repeat defects |
| Innovation & Creativity | **25%** | Originality, differentiation, Gen AI beyond a superficial implementation | "AI proposes, data decides, human approves"; reads messy Excel instead of needing an MES; bilingual customer reply; quality memory |
| User Experience & Solution Design | **10%** | Usability, accessibility, how well the parts work together | Phone-first, live agent trace, editable 8D with clickable citations, one-tap approve |

---

## 3. Hackathon constraints (hard rules)

| Rule | What it means for us |
|---|---|
| Must use Google AI models (Gemini/Gemma) or a Google agentic platform | Gemini via **Vertex AI** for every AI step; agents built with **Google ADK** |
| Must be built on the Google Cloud stack and deployed on Cloud Run / GCP / Firebase | Backend on Cloud Run, frontend on Firebase Hosting (weekend) |
| Working end-to-end prototype, not a mockup | The real flow must run on real data and real model calls |
| Public GitHub repo, demo video under 3 minutes, PDF deck | Repo must be clean, README complete, no secrets |
| Fresh project, all materials in English | Customer reply is in Japanese + English, everything else English |

**Judging weights:** see section 2.5.

**Open items to confirm (not blockers for code):** submission deadline (team's working date is Sun 18 Oct; official FAQ only lists team formation closing 14 Oct), whether Hack2skill gives participant credits (not stated in the official FAQ).

---

## 4. Problem

**Challenge statement (plant manager's voice):**
"When a customer sends a defect complaint, my quality team has about a day to contain it and a few weeks to send an 8D the customer will accept. My engineers spend days pulling lot records out of Excel and oven printouts. When the deadline wins, the root cause becomes 'operator error', the 8D gets sent back, and the same defect returns next quarter."

**Why AI is needed (not just a form):**

| Step | AI capability | Why it needs AI |
|---|---|---|
| Read defect photo | Gemini multimodal vision, structured output | Image input |
| Read complaint + messy Excel lot sheet | Gemini extraction, structured output | Unstructured text and messy spreadsheets (answers "what if there is no MES?") |
| Propose root causes | Agent reasoning + function calling over the 6Ms | Planning which data to pull and which causes are testable |
| Find evidence in documents | RAG with page/row citations | Meaning-based match ("solder bridging" ↔ "peak temperature above limit") |
| Write the 8D | Grounded long-form generation | Customer-grade technical writing with citations |
| Customer reply | Japanese (business keigo) + English | Translation with correct tone |
| Quality memory | Embeddings + vector search | Similarity of past cases, not keywords |
| Know when to stop | "Insufficient evidence — escalate" | Judgement over results |

**What AI never does:** decide if a cause is true (statistics do), invent numbers, or take actions without human approval.

---

## 5. Users

**Primary user (logged in):** **Priya R.** — Quality Engineer, Sree Electronics (fictional), Chennai, SMT Line 2. Receives the complaint, runs the investigation, edits and approves the 8D.
- Login is a **fixed demo profile** (avatar initials "PR", name, role, plant). No real authentication. Her name is stamped on approvals and edit history.

**Company focus:** the product is built for a **segment, not a named company**: Tier-2/3 electronics (PCB assembly) suppliers in India and ASEAN that ship to Japanese and Korean automotive OEMs. We demo it at **one fictional plant**, "Sree Electronics (fictional), Chennai", so the story stays concrete. We don't use a real company because we have no real data, real logos would raise branding and permission issues, and a segment framing scores better on impact and scalability.

**Other roles (shown, not logged in):** Quality Manager (CAPA owner), Maintenance Lead (receives work order), Customer SQE at "Hoshino Denso (fictional)" (receives reply).

---

## 6. Scope

**In scope (today):** the 6 screens below, the full agent flow, synthetic plant data + documents, approval actions, quality memory, mobile-responsive UI, running locally against real Google Cloud services.

**Weekend:** Cloud Run + Firebase Hosting deployment, demo access code, README polish, video, deck.

**Out of scope:** real authentication, real MES/ERP integration, multi-tenant, notifications/email sending (reply is drafted, not sent), PDF export of the 8D (stretch goal).

---

## 7. Screens

Phone-first (390 px) and desktop (1280 px). Bottom tab bar on mobile, left sidebar on desktop. Header on every screen: **8D Copilot logo** · "Sree Electronics (fictional), Chennai" · user chip "Priya R. · Quality Engineer". Footer on every screen: "Synthetic demo data · Built with Gemini on Google Cloud".

| # | Screen | Route | What the user sees | AI approach |
|---|---|---|---|---|
| 0 | **Complaints inbox (Home)** | `/` | Open complaints as cards: customer, product, lot, defect, "8D due in N working days" countdown (amber when ≤ 3). Past investigations list. Link to Quality Memory. | Gemini structured extraction turns raw complaint text into fields (customer, product, lot, defect, qty, due date). Cached after first run. |
| 1 | **New investigation** | `/new?complaint=C-2026-031` | Photo upload (camera on phone), complaint text prefilled, lot field prefilled, optional upload of the messy lot-traveler Excel, "Start investigation" button. | Gemini vision returns defect type, severity, bounding box, confidence, one-line visual evidence (strict JSON). Shown on the photo as soon as it returns. |
| 2 | **Live investigation** | `/inv/:id` | Photo with defect box + chip ("Solder bridge · Major · 86%"). Live timeline of agent steps (agent, title, time). Hypothesis cards with verdict pills: Supported (green), Rejected (grey), Inconclusive (amber), p-value in monospace. Rejected cards stay visible. "Similar past case found" row when memory hits. "Review 8D" button on draft_ready. | ADK multi-agent orchestration with function calling. Investigator proposes 3–5 testable hypotheses across the 6Ms and calls the statistics tool; it relays the verdict, never creates one. Events stream via SSE. |
| 3 | **Evidence** | `/inv/:id/evidence` | Chart: reflow peak temperature by lot (Line 2 highlighted, defect lots marked, vertical line "WO-388 maintenance", horizontal line "250 °C limit"). Per-hypothesis stats table. Citation cards: "PFMEA row 14", "Control plan item 6", past 8D, each with quote + source + page/row. | RAG (Vertex AI RAG Engine) returns document passages with source and page/row. The chart and numbers come from the statistics tool, not the LLM. |
| 4 | **8D review** | `/inv/:id/review` | D1–D8 collapsible, editable (auto-grow textarea). Citation chips open a side sheet with the source. Proposed actions with toggles: CAPA, hold lots, work order, customer reply. Optional note. "Approve 8D" button. If status is `insufficient_evidence`: banner explaining missing data, Approve hidden. | Gemini grounded writing with JSON output. Every factual sentence carries a citation; numbers only from tool results. |
| 5 | **Actions done + memory** | `/inv/:id/done` | "8D approved by Priya R." header. Cards: CAPA-0142, Lot hold H-77 (lot list), Work order WO-412. Customer reply card in Japanese with English toggle and Copy button. "Saved to quality memory" card with confirmed root cause. | Gemini writes the bilingual reply. Embedding of the confirmed cause stored for vector search. Records are created by plain code. |

**Also:** a simple **Quality Memory** list page (`/memory`) showing saved confirmed causes (can be a section of the inbox if time is short).

---

## 8. The demo flow (golden path)

1. Inbox shows complaint **C-2026-031** from Hoshino Denso (fictional): "Solder bridging on ECU-PCB-7, lot 2611, 14 of 500 units, 8D within 10 working days."
2. Priya taps it → New investigation → uploads the defect photo (and the messy Line 2 Excel lot sheet) → Start.
3. Vision: "Solder bridge · Major · 86%" with box on the photo.
4. Investigator proposes and tests:
   - H1 Stencil wear → **Rejected** (Line 2 had a new stencil, print counts are low)
   - H2 Reflow peak temperature drift on Line 2 after WO-388 → **Supported** (≈ +8 °C, above the 250 °C limit, p < 0.01)
   - H3 Solder paste / room humidity → **Rejected**
   - H4 Operator change (OP-17 joined Line 2 shortly before) → **Inconclusive** (confounded in time with WO-388)
5. Evidence: chart shows defect lots after the WO-388 line; PFMEA row 14 and Control plan item 6 cited; WO-388 shows "profile verification pending" (the escape point).
6. 8D review: Priya edits D4, turns off one action, approves.
7. Actions: CAPA-0142, hold on L2609–L2614, WO-412 "Verify and re-qualify reflow profile Line 2", Japanese + English reply, saved to memory.
8. **Memory moment:** start an investigation for lot 2613 → timeline shows "Similar past case found: CAPA-0142", tests that hypothesis first.
9. **Edge case:** a photo with no defect ends in "Insufficient evidence — escalate".

---

## 9. AI design

### 9.1 Golden rule
The LLM **proposes**. Deterministic Python **decides**. A human **approves**. The LLM never writes p-values, measurements or verdicts; the writer may only use numbers present in tool results.

### 9.2 Agents (Google ADK, Python)

| Agent | Type | Tools | Output |
|---|---|---|---|
| `root_agent` | Orchestrator (sequential) | sub-agents | Emits SSE events, manages state |
| `intake_agent` | LLM | `parse_complaint`, `parse_lot_traveler` | Complaint fields; lot rows extracted from messy Excel (with a confidence flag per field) |
| `vision_agent` | LLM (multimodal) | `analyze_defect_image` | `Defect` JSON |
| `investigator_agent` | LLM with function calling | `search_quality_memory`, `get_lot_genealogy`, `get_process_window`, `get_maintenance_events`, `get_comparison_groups`, `test_hypothesis` | 3–5 hypotheses, each with one measurable parameter or event, each with its tool-returned verdict |
| `evidence_agent` | LLM + RAG | `search_quality_docs` | Citations (source file, page/row, quote) |
| `writer_agent` | LLM | none (reads state) | D1–D8 JSON with citations, or `insufficient_evidence` with what data is missing |
| `actions` (after approval) | Plain code + one LLM call | `create_capa`, `hold_lots`, `create_work_order`, `draft_customer_reply`, `save_quality_memory` | Records + bilingual reply |

### 9.3 Statistics tool (`test_hypothesis`) — no LLM inside
- Input: hypothesis id, parameter (column) or event (work order id), expected direction (`higher` / `lower` / `any`), lot id.
- Comparison groups: defect lots vs good lots of the same product in the last 30 days. For a maintenance-event hypothesis: same line, lots before vs after the event date.
- Tests: Welch t-test (numeric), Fisher exact (categorical, e.g. operator), simple before/after change-point by date.
- **Direction-aware verdict (MUST):** `supported` only if p < 0.01 **and** the effect is in the hypothesised direction **and** the effect is meaningful (e.g. ≥ 3 °C for temperature). `rejected` if p > 0.1 **or** the effect is in the opposite direction. Otherwise `inconclusive`.
- Output: verdict, p-value, effect size with unit, group sizes, chart PNG (matplotlib) saved to Cloud Storage, chart URL.

### 9.4 Prompts (store in `agent/prompts/*.md`)
- **Vision:** automated optical inspection assistant; look only at what is visible; single most important defect; enums `solder_bridge | missing_component | misalignment | scratch | contamination | other | none`; severity rules (critical = short circuit/safety, major = functional failure, minor = cosmetic); box as 0–1 fractions; never guess the cause.
- **Investigator:** propose 3–5 hypotheses across Machine, Method, Material, Man, Measurement, Environment; each must name ONE parameter from the process table or one maintenance event plus the expected direction; check quality memory first; call `test_hypothesis` for every hypothesis and accept its verdict; never write numbers yourself.
- **Writer:** experienced supplier quality engineer writing to a Japanese automotive customer (IATF 16949). D3 names exact lots on hold. D4 states cause, how verified (test, p-value, effect) and why it escaped (WO-388 profile verification pending). D5/D6 permanent fix and effectiveness check. D7 updates the cited PFMEA and control plan rows. Never "operator error" as a root cause. Every factual sentence ends with a citation in brackets, e.g. `[PFMEA row 14]`, `[Chart: reflow peak temp by lot]`.
- **Customer reply:** short, polite business Japanese (keigo) + English; containment, root cause, permanent fix, CAPA number.

### 9.5 Structured output
Every LLM call that feeds code uses JSON schema / structured output and is validated with Pydantic. On validation failure: one retry, then an `error` event.

### 9.6 Guardrails
- Model name only from `GEMINI_MODEL` env var; embedding model from `EMBED_MODEL`.
- No hypothesis without a measurable parameter or event.
- No number in the 8D that is not in a tool result (check with a simple post-validation pass).
- No image bytes or secrets in logs.

---

## 10. Synthetic data spec (`data/`)

**All data is synthetic and labelled so in the UI, README and deck.** Ranges are shaped on public SMT references.

### 10.1 Realism references (from web research)
- SAC305 lead-free solder melts at ~217 °C; typical profile: preheat ramp 1–3 °C/s, soak 150–180 °C for 60–120 s, peak 235–250 °C. Too-fast heating or exceeding the recommended peak can make solder flow uncontrollably → bridging. (ALLPCB reflow troubleshooting guide)
- Textbook bridging causes used for hypotheses/decoys: hot slump during ramp-up, excess paste deposit / stencil issues, excess squeegee pressure, paste viscosity / humidity (cold slump), placement pressure. (AIM Solder SMT troubleshooting guide)

### 10.2 Plant and tables (BigQuery dataset `plant`)
- **Plant:** Sree Electronics (fictional), Chennai. Product ECU-PCB-7. Lines L1 and L2, shifts A/B/C. ~64 lots (L2551–L2614) over 30 days ending 13 Oct 2026, ~500 boards each.
- `lots`: lot_id, line, shift, date, product, qty, paste_lot, stencil_id, operator_id, defects_solder_bridge, defects_other, defect_rate, ship_status.
- `process`: lot_id, reflow_peak_temp_c, time_above_liquidus_s, preheat_ramp_c_per_s, soak_time_s, conveyor_speed_cm_min, paste_age_h, room_humidity_pct, stencil_print_count, squeegee_pressure_kg.
- `maintenance`: wo_id, line, date, asset, description, status, post_check. Include ~10 work orders, among them **WO-386** (2026-10-07, Line 2, new stencil ST-07B installed) and **WO-388** (2026-10-08, Line 2, "Reflow oven zone 7 heater element replaced, profile re-tuned by vendor", post_check = `profile_verification_pending`).
- `complaints`: C-2026-031 (open, the golden case, lot 2611, 14 of 500, due 29 Oct), C-2026-032 (open, tombstoning on ECU-PCB-9 from "Kaveri Motors (fictional)"), C-2026-024 (closed, tombstoning, links to a past 8D).

### 10.3 Planted truth and decoys (MUST pass `data/check_plant.py`)

| Hypothesis | How it is built into the data | Required verdict |
|---|---|---|
| H2 Reflow peak temp drift, Line 2 after WO-388 | Line 2 lots after 2026-10-08 (L2609–L2614): peak 253 ± 1.5 °C vs normal 245 ± 1.5; TAL ~82 s vs ~62 s; bridge rate ~2.6% vs ~0.3%. Lot 2611 = exactly 14 bridges. | **supported** |
| H1 Stencil wear | Line 2 got a **new** stencil the day before; defect lots have **low** print counts. Direction-aware test → opposite direction. | **rejected** |
| H3 Humidity | Uniform 45–60%, independent of everything. | **rejected** |
| H4 Operator change | OP-17 starts on Line 2 on 2026-10-06 and also works some normal lots, so the signal is weak and confounded in time. Tune the data until Fisher p is between 0.01 and 0.1. | **inconclusive** |
| Paste age | Random, independent. | **rejected** (if proposed) |

- Baseline lots must not cross the "defect lot" threshold by noise (keep baseline bridge rate low and cap noise), so defect lots = the drift window.
- Fixed random seed. `check_plant.py` prints a verdict table and **asserts** the required verdicts.

### 10.4 Unstructured inputs
- `lot_traveler_line2_wk41.xlsx`: messy Excel filled by shift leads — title rows above the header, short column names ("Lot#", "Dt", "Opr", "Oven peak (C) [from printout]"), dates as dd/mm, one cell "same as prev", free-text remarks ("bridges near U7 QFP fine pitch - reworked 9, rest shipped", "oven done after maint, ok to run per vendor"). This is the "works without an MES" input.
- Defect photos: public **VisA** dataset PCB subsets (CC BY 4.0). Pick 3–5 images where Gemini reliably reports a defect, plus 1 image with no defect for the edge case. If no VisA image reads as a solder bridge, use a team photo of a real board and say so.

### 10.5 Quality documents (RAG corpus `quality-docs`, Cloud Storage `docs/`)
Generate as PDF (or Markdown if PDF is slow), each with footer "Synthetic document for demo purposes":
- **PFMEA** (AIAG-VDA 2019 style) for SMT reflow, ~20 numbered rows. **Row 14:** failure mode "Solder bridging", cause "Reflow peak temperature above profile limit", prevention "Profile verification after any oven maintenance", detection "AOI 100% + profile check per shift".
- **Control plan** for the SMT line. **Item 6:** "Reflow profile verification after maintenance; reaction plan: hold lots, re-profile".
- **Past 8D #1:** tombstoning from paste age (links to C-2026-024).
- **Past 8D #2:** voids from a nitrogen supply problem.

---

## 11. Architecture and tech stack

```
Phone / browser (React PWA-style SPA)
        │  REST + SSE
        ▼
FastAPI + Google ADK agents (Python 3.12)  ── local today, Cloud Run on weekend
   │            │              │              │
   ▼            ▼              ▼              ▼
Gemini via   BigQuery       Firestore       Cloud Storage
Vertex AI    (plant data)   (investigations,(photos, docs,
(vision,                     CAPA, holds,    charts)
 reasoning,                  work orders,
 writing,                    memory + vector
 embeddings)                 search)
   │
   ▼
Vertex AI RAG Engine (PFMEA, control plan, past 8Ds → cited passages)
```

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind; Chart.js; EventSource (SSE); react-router |
| Backend | Python 3.12, FastAPI, Uvicorn, Google ADK, `google-genai` SDK (Vertex AI mode), Pydantic |
| Model | Current GA **Gemini Flash** model on Vertex AI (check Model Garden for ID and region) via `GEMINI_MODEL`; embeddings via `EMBED_MODEL` |
| Statistics | pandas, scipy, matplotlib |
| Plant data | BigQuery dataset `plant` |
| App state | Firestore (Native mode): `investigations`, `events`, `capa`, `holds`, `work_orders`, `memory` (with vector index) |
| Files | Cloud Storage bucket `<project>-assets` (`images/`, `docs/`, `charts/`) |
| Document search | Vertex AI RAG Engine corpus `quality-docs` |
| Hosting (weekend) | Cloud Run service `api` (min-instances 1, 300 s timeout for SSE); Firebase Hosting with `/api/**` rewrite to Cloud Run |
| CI (weekend, optional) | GitHub Actions with Workload Identity Federation |

### 11.1 Google Cloud setup (do first, ~1 hour)
- New Google account → Google Cloud **free trial ($300, 90 days, card needed for verification, no auto-charge)**. Create project (e.g. `8d-copilot-2026`), set a budget alert.
- Enable: Vertex AI, BigQuery, Firestore, Cloud Storage, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Firebase.
- Use Gemini **through Vertex AI** (covered by trial credits). **Do not** rely on an AI Studio API key for the app: trial credits don't cover it. AI Studio is only for testing prompts.
- Local auth: `gcloud auth application-default login` + `gcloud config set project <id>`. No keys in code.
- Add team members in IAM (Vertex AI User, BigQuery Data Editor + Job User, Storage Object Admin, Cloud Datastore User, Cloud Run Developer, Firebase Hosting Admin).
- Region: `asia-south1` for data/storage/Firestore; model and RAG calls in a region where the chosen model and RAG Engine are available (record in README).

### 11.2 Environment variables (`.env.example`)
`GCP_PROJECT`, `GCP_REGION`, `VERTEX_REGION`, `GEMINI_MODEL`, `EMBED_MODEL`, `BQ_DATASET=plant`, `GCS_BUCKET`, `RAG_CORPUS`, `FIRESTORE_DB=(default)`, `DEMO_ACCESS_CODE` (weekend), `VITE_API_URL`, `VITE_USE_MOCKS`.

### 11.3 Repo layout
```
8d-copilot/
  agent/            FastAPI app, ADK agents, tools, prompts, tests
    main.py  models.py  agents/  tools/  prompts/  tests/
  data/             generate_plant.py, check_plant.py, docs/, images/, out/
  infra/            load_data.sh, build_rag.py, Dockerfile, run_cases.py
  web/              React app (src/, design/)
  docs/contract/    README.md (API), mock_events.json, mock_investigation.json
  README.md  .env.example  CLAUDE.md
```
Add a `CLAUDE.md` with the golden rule, the contract rule, and "model name only from env".

---

## 12. API contract (`docs/contract/README.md`)

Base: `{API_URL}/api`

1. `GET /complaints` → list of complaints with parsed fields and due-date countdown.
2. `POST /investigations` (multipart: `image`, `complaint_id`, `complaint_text`, `lot_id`, optional `traveler` xlsx) → `{ "id": "inv_123", "status": "running" }`
3. `GET /investigations/{id}/events` (SSE). Each event:
   ```json
   { "seq": 4, "ts": "2026-10-16T10:02:11Z",
     "agent": "intake | vision | investigator | evidence | writer | system",
     "type": "step_started | tool_call | tool_result | memory_hit | hypothesis | hypothesis_result | citation | draft_ready | done | error",
     "title": "Testing: reflow peak temperature drift on Line 2",
     "detail": "Welch t-test, defect lots vs good lots",
     "data": {} }
   ```
   `hypothesis_result.data`: `{ "hypothesis_id": "H2", "verdict": "supported|rejected|inconclusive", "p_value": 0.003, "effect": "+8.1 °C mean peak temp", "n_defect": 6, "n_good": 58, "chart_url": "..." }`
4. `GET /investigations/{id}` → full state: `status` (`running | draft_ready | approved | insufficient_evidence`), `defect {type, severity, box[x,y,w,h], confidence, visual_evidence}`, `hypotheses[]`, `eight_d {D1..D8: {text, citations[{label, source, ref}]}}`, `proposed_actions[{id, kind: capa|hold|work_order|customer_reply, summary}]`.
5. `POST /investigations/{id}/approve` body `{ "approver": "Priya R.", "edits": {"D4": "..."}, "rejected_action_ids": ["A3"], "note": "..." }` → `{ "capa_id", "hold_id", "work_order_id", "replies": {"ja", "en"}, "memory_id" }`
6. `GET /memory` → saved confirmed causes.
7. `GET /health` → `{ "ok": true, "model": "<GEMINI_MODEL>" }`

Commit `mock_events.json` (15–18 events for the golden path) and `mock_investigation.json` so the UI can be built with `VITE_USE_MOCKS=true` (replay one event every 600 ms).

---

## 13. Non-functional requirements

- **Responsive (MUST):** works at 390 px and 1280 px, no horizontal scroll, camera upload on mobile, touch targets ≥ 44 px.
- **Look:** calm, technical. Light theme with deep green accent; amber only for warnings/inconclusive; dark mode supported. Sans font for text, monospace for IDs, p-values and numbers.
- **Accessibility:** visible focus, alt text, verdict pills carry text (not colour only), respects reduced motion.
- **Latency:** first visible result (defect box) < 10 s; full golden path < 90 s.
- **Reliability:** a **replay mode** that plays a saved successful run if the network fails during recording; live mode is default.
- **Security:** no secrets in repo or logs; Firestore written only by the API; demo access code on deployed version.
- **Honesty:** "Synthetic demo data" label on every screen; dataset credits in README (VisA CC BY 4.0).
- **Cost:** stay within the $300 trial; log tokens per investigation.

---

## 14. Branding

- Product logo: simple "8D Copilot" wordmark with a small mark (SVG, made in-house).
- Plant name: "Sree Electronics (fictional), Chennai". Customer: "Hoshino Denso (fictional)".
- No real company logos, no Google logos. Footer text only: "Built with Gemini on Google Cloud".

---

## 15. Build phases for Claude Code (today)

| Phase | Deliverable | Done when |
|---|---|---|
| 0. Setup | Repo skeleton, `CLAUDE.md`, `.env.example`, contract + mock JSON, Pydantic models | Contract and mocks committed |
| 1. Data | `generate_plant.py`, `check_plant.py`, messy Excel, 4 quality docs, demo images | `check_plant.py` asserts all required verdicts |
| 2. Cloud load | `infra/load_data.sh` (BigQuery + GCS), `infra/build_rag.py` (RAG corpus, prints name + test query) | Test query returns PFMEA row 14 with source |
| 3. Tools | vision, plant_data, stats_test, rag search, memory, unit tests (CSV-based, no cloud) | Tests pass |
| 4. Agents + API | ADK agents, FastAPI endpoints, SSE, Firestore state | Golden path runs locally; H2 supported, H1/H3 rejected, H4 inconclusive, cited 8D draft |
| 5. UI | 6 screens on mocks, then on the real local API | Full flow on a phone-sized window |
| 6. Actions + memory | Approve endpoint, bilingual reply, memory + "similar past case" | Lot 2613 run shows memory hit |
| 7. Hardening | `infra/run_cases.py` (golden lot, 2 other drift lots, 2 good lots, 1 Line 1 lot, 1 no-defect photo), replay mode | ≥ 6 of 7 cases pass |

**Weekend:** Dockerfile, Cloud Run deploy, Firebase Hosting with rewrite, demo access code, README (what it does, architecture, how to run, what is synthetic, credits), public GitHub repo, video (< 3 min), PDF deck (vision, problem, benefit, feasibility, scalability).

---

## 16. Success metrics (for deck)

- Time from complaint to evidence-backed 8D draft (target: minutes vs days).
- Share of hypotheses tested with data (target 100%).
- Customer 8D rejection rate and repeat-defect rate (pilot metrics).
- Every 8D claim traceable to a source (target 100%).

---

## 17. Risks and judge questions

| Risk / question | Answer built into the product |
|---|---|
| "You planted the cause — it's theatre." | LLM only proposes; statistics decide; rejected and inconclusive hypotheses stay on screen; data openly labelled synthetic. |
| "A Tier-2 plant has no MES." | Agent reads the messy Excel lot sheet and oven printout values. |
| "8D generators already exist." | Ours tests causes against data, cites every claim, acts after approval, and remembers confirmed causes. |
| "Is it just paperwork?" | It closes the loop: lot hold, maintenance work order, CAPA, customer reply, memory. |
| Vision misreads VisA images | Pre-test images in AI Studio; keep a backup photo. |
| Network failure during recording | Replay mode. |
| Free-trial limits | Gemini through Vertex AI (covered by credits); budget alert set. |

---

## 18. Sources for realism data
- ALLPCB, "Troubleshooting Reflow Soldering Defects: A Practical Guide for Engineers" — https://www.allpcb.com/blog/pcb-assembly/troubleshooting-reflow-soldering-defects-a-practical-guide-for-engineers.html
- AIM Solder, "SMT Troubleshooting Guide" — https://aimsolder.com/sites/default/files/documents/smt_ts.pdf
- Google Cloud free trial terms — https://docs.cloud.google.com/free
- AI Builder Cup FAQ — https://aibuildercup.com/Faqs.html
- AI Builder Cup themes and judging criteria — https://aibuildercup.com/themes.html
- VisA dataset (Amazon Science, CC BY 4.0) — check licence page when downloading
