# 8D Copilot — judge deck

Content and design rules for the submission deck.
**Google Cloud AI Builder Cup 2026 · Manufacturing · JAPAC**

Every figure below was read from the live deployment on 18 October 2026. If you
change the data, re-read them — a wrong number in front of a judge costs more
than a missing one.

- Live: **https://d-copilot-2026.web.app** · access code **demo-b1b20c**
- API: `https://api-166753422106.asia-south1.run.app/api/health`

---

## Design rules

Follow these or the deck will look like a student project. They matter more than
the words.

**Type.** Two faces, no more. **Fira Sans** for everything, **Fira Code** for
numbers, IDs and p-values — the same pairing as the product, so the deck and the
app read as one thing. Title 40–44pt, body 20–24pt, never below 18pt. A judge
reads it on a laptop at the back of a room.

**Colour.** Deep green `#1B5E3F` is the only brand colour. Amber `#B7791F` means
*warning* or *inconclusive* and nothing else. Grey `#6B7670` for rejected. Red
only for genuine failure. Never colour alone — every status carries a word.

**One idea per slide.** If a slide needs two sentences to explain, it is two
slides. Ten slides is the target; twelve is the ceiling.

**Numbers get the stage.** When a slide exists to deliver a figure, set that
figure at 60pt+ and let the rest be small. `p = 0.000221` deserves a slide of
its own more than a bullet list does.

**Screenshots over diagrams.** You have a working product. A real screenshot of
the live trace beats any architecture drawing. Crop tight, no browser chrome, no
desktop background.

**No stock imagery.** No gears, no robot hands, no glowing brains. A photograph
of the actual defect board is worth more than every stock image ever made.

**No logos you do not own.** Google Cloud's name in text is fine; their logo is
not. The plant and customers are fictional and must stay labelled as such.

**Space.** Margins of at least 60px. Crowding reads as panic.

---

## Slide 1 — Title

> **8D Copilot**
> The AI proposes. The data decides. A human approves.
>
> Google Cloud AI Builder Cup 2026 · Manufacturing · JAPAC
> Sabari Srinivas · Susan Subramani · Vishwaa

Deep green background, white type. Nothing else. The tagline is the whole pitch —
let it carry the slide alone.

---

## Slide 2 — The problem, in a plant manager's voice

Quote it verbatim, large, as a quotation:

> *"When a customer sends a defect complaint, my quality team has about a day to
> contain it and a few weeks to send an 8D the customer will accept. My engineers
> spend days pulling lot records out of Excel and oven printouts. When the deadline
> wins, the root cause becomes 'operator error', the 8D gets sent back, and the
> same defect returns next quarter."*

Three failures hide in that quote, and the product answers all three. Say so in
one line at the bottom: **days of work · a root cause nobody believes · a defect
that comes back.**

---

## Slide 3 — What it does

A single flow, left to right, five steps, no sub-bullets:

**Photo + complaint → defect identified → causes tested against factory data →
cited 8D drafted → human approves → CAPA, lot hold, work order, bilingual reply,
memory**

Underneath, one line: *Minutes, not days — and every claim traceable to a source.*

---

## Slide 4 — The thing nobody else does

This is the slide that wins or loses the 40% technical criterion. Give it the
biggest number on the deck.

> ## The AI never decides
>
> It proposes hypotheses. **scipy decides.**

Then the live verdicts from the golden path, set in mono:

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Reflow peak temperature drift after WO-388 | **Supported** | p = 0.000221, +7.6 °C |
| Stencil wear | Rejected | effect −29,615 prints — wrong direction |
| Room humidity | Rejected | p = 0.978 |
| Operator change | Inconclusive | Fisher p = 0.0177, confounded in time |

**The stencil row is the one to talk about.** It correlates strongly with the
defects — but in the *opposite* direction, because Line 2 got a brand-new stencil
the day before. A p-value-only system would have called it the root cause. The
direction rule rejects it before the p-value is even consulted.

That sentence is your answer to *"did you just plant the answer?"*

---

## Slide 5 — See it decide

A screenshot of the live trace, cropped tight. The labels do the work:

- **"Computed from lot data · Welch t-test, p = 0.0002"** beside a verdict
- **"AI-drafted · edit before approving"** beside the 8D

One line underneath: *The division of labour is visible on screen, not claimed in
a slide.*

---

## Slide 6 — The evidence

Screenshot of the reflow chart: 64 lots, Line 1 against Line 2, the WO-388
maintenance line, the 250 °C limit.

One line: *Line 1 runs at 0.41%. Line 2 at 0.76%. The drift starts at the
maintenance that was never verified.*

**Be precise, and the precision is the point:** lot L2611 — the lot the customer
complained about — is itself *below* the limit at 248.7 °C. Five of the six lots
in the window breach it. So the 8D states the cause at the **window** level, never
the lot level. A judge who checks will find the product was more careful than it
needed to be.

---

## Slide 7 — It remembers, and it checks

Two halves.

**Left — memory.** A second investigation on lot L2613 retrieves the first by
meaning, not keyword: cosine similarity **0.693**, naming CAPA-0142.

**Right — effectiveness.** The part no one does. When a defect matches a past
CAPA, the same statistics ask: *did that fix actually work?* On CAPA-0098 the
answer is **`never_worked`** — a corrective action signed off without changing
the defect rate.

One line: *Industry research says the measure of a CAPA system is the recurrence
rate, not the number closed. We measure it.*

---

## Slide 8 — Built for a plant that has no MES

Three inputs, three icons, no paragraphs:

- **A photo** taken on a phone
- **The spreadsheet** the shift leads actually fill in — title rows above the
  header, `dd/mm` dates, and the literal text *"same as prev"* where a temperature
  should be, flagged as low-confidence rather than guessed
- **A voice note, spoken into the page** — press the mic, say *"bridging again on line
  two, oven's been odd since the vendor came in"*, press it again. English, Tamil or
  Hindi. No file to prepare, no speech-to-text service in between: Gemini reads the
  audio itself.

One line: *No MES. No integration project. The inputs a Tier-2 plant already has.*

**Worth demonstrating live if the room allows it** — the mic is the one thing on screen
a judge can try themselves in ten seconds, and watching the transcript appear in their
own voice does more than any slide about multimodality. It records in the browser, so it
works from their laptop over the deployed URL.

---

## Slide 9 — Architecture

Keep it plain. One row of boxes:

**React + Vite** → **FastAPI on Cloud Run** → **Gemini 2.5 Flash on Vertex AI**
→ **BigQuery · Firestore · Vertex RAG · Cloud Storage**, all `asia-south1`

Underneath, the capabilities as a single line of text, not boxes:

*Multimodal vision · audio understanding · schema-validated structured output ·
agentic hypothesis generation · tool use · RAG with row-level citations ·
embeddings and vector search · grounded generation with number-provenance
checking · bilingual keigo*

Then one sentence that is worth more than the diagram: **No API key. The service
authenticates as itself through Vertex AI.**

---

## Slide 10 — Honest limits

Put this in. A judge who finds a limitation you listed trusts everything else;
one who finds a limitation you hid stops trusting all of it.

- All plant data is synthetic and the root cause is **planted on purpose** —
  `python -m data.check_plant` lets you watch the decoys get rejected
- No collinearity check, which is *why* stencil identity is deliberately excluded
  as a testable parameter
- Vision reads are majority-stable, not deterministic
- The approval lock is per-process; multi-instance would need a Firestore
  transaction

One line: *We would rather you find these here than find them yourselves.*

---

## Slide 11 — Impact

Four figures, mono, large:

| | |
|---|---|
| First-pass yield measured across | **31,973 units** |
| Hypotheses tested against data | **100%** |
| Claims traceable to a source | **100%** |
| Complaint to cited 8D draft | **~40 seconds** |

One line: *Days of engineering work become one approval.*

---

## Slide 12 — Close

> **The AI proposes. The data decides. A human approves.**
>
> https://d-copilot-2026.web.app · code demo-b1b20c

Same deep green as slide 1. The deck ends where it started.

---

## Things to have ready for questions

| Likely question | Answer |
|---|---|
| *Did you plant the answer?* | Yes, and openly — three decoys are planted too, and the statistics reject them. Run `check_plant` yourself. |
| *Is the AI really looking at the photo?* | Upload your own board. It is a live Gemini call, not a lookup. |
| *What if two causes are confounded?* | The operator hypothesis is — it returns **inconclusive** at p = 0.0177 rather than guessing. |
| *Does it work on a new case?* | Yes — six lots in our harness, six independent investigations. Lot L2601 came back *insufficient evidence* with four rejected. |
| *Why not ADK?* | Gemini via Vertex AI satisfies the rule. We built the orchestration directly so the statistics stay outside the model's control. |
| *What if the model is wrong?* | It cannot set a verdict. The worst it can do is propose a bad hypothesis, which the data then rejects. |

---

## Before you present

- [ ] Re-read every figure here against the live site — data changes, slides do not
- [ ] Have a native reader check the Japanese reply is business keigo
- [ ] Open the app on a phone and a laptop
- [ ] Set `REPLAY_CASE=golden` if the network or quota is uncertain — it announces
      itself as replay, so you are never misrepresenting it
- [ ] Point at **CAPA-0098** for the effectiveness story; the other CAPAs honestly
      report *insufficient data*
- [ ] Do not click the Kaveri Motors complaint — it references a lot outside the
      dataset and will not investigate

---

# Appendix A — every AI feature, and what it actually does

Verified against the codebase on 18 October 2026. Seven agents, seven prompts,
one model family. Each row names the file so a judge can check.

## The agents

| # | Agent | What the model does | Where |
|---|---|---|---|
| 1 | **Vision** | Reads a defect photo and returns type, severity, a bounding box as 0–1 fractions, confidence, and one sentence of visual evidence. Forbidden from guessing a cause — appearance only. | `agents/vision.py`, `tools/vision_tool.py` |
| 2 | **Intake** | Turns free-text customer prose into structured fields — customer, product, lot, quantities, due date. Leaves a field empty rather than inventing it. | `agents/intake.py`, `tools/intake_tools.py` |
| 3 | **Voice** | Extracts evidence from a shift lead's spoken note: lot or line, observations, maintenance mentions, transcript. Detects the language, translates, and flags anything half-heard. Recorded **live in the browser** — press the mic, talk, press it again. | `tools/voice_tool.py`, `components/VoiceRecorder.tsx` |
| 4 | **Investigator** | Proposes 3–5 hypotheses across the 6Ms, each naming exactly one measurable parameter or maintenance event plus an expected direction. Checks quality memory first. **Relays every verdict; never forms one.** | `agents/investigator.py` |
| 5 | **Evidence** | Turns the supported hypothesis into a retrieval query and returns passages with source, row reference and quote. | `agents/evidence.py`, `tools/doc_search.py` |
| 6 | **Writer** | Drafts D1–D8. Every factual sentence carries a citation; numbers may come only from tool results. Never "operator error". | `agents/writer.py` |
| 7 | **Reviser** | A different job from writing: reads the customer's rejection of a previously submitted 8D and amends the failing sections — grounded editing against a critique. | `agents/reviser.py` |
| 8 | **Actions** | One model call writes the customer reply in Japanese business keigo and English. Every record is created by plain code. | `agents/actions.py` |

## The capabilities, named the way a judge will score them

| Capability | Evidence it is real |
|---|---|
| **Multimodal vision** | Live Gemini call on an uploaded photo; a judge can upload their own |
| **Audio understanding** | Same `generate_content` path, audio bytes instead of image — no separate speech service. Captured from the judge's own microphone, in their own language |
| **Structured output** | Every model call validated against a Pydantic schema; one retry, then a hard error |
| **Agentic reasoning** | Hypotheses proposed across the 6Ms, each tied to a testable parameter |
| **Tool use with the model subordinate** | `test_hypothesis` returns the verdict; the agent relays it even when it contradicts the hypothesis |
| **RAG with citations** | Row-level references — `PFMEA row 14`, `Control plan item 6` — with the quoted text |
| **Embeddings and vector search** | Quality memory retrieved by meaning: 0.693 cosine on the lot L2613 run |
| **Grounded long-form generation** | D1–D8 with a provenance pass that rejects any number absent from a tool result |
| **Controlled register** | Japanese business keigo, not literal translation |
| **Statistical adjudication** | Welch t-test and Fisher exact, direction-aware, in `tools/stats_verdict.py` |
| **Effectiveness verification** | Did a past CAPA work? `never_worked` on CAPA-0098 |

## What the model is forbidden to do

Worth a line in the deck, because it is the architecture:

- it cannot write a p-value, a measurement or a verdict
- it cannot propose a hypothesis without a measurable parameter or event
- it cannot put a number in the 8D that no tool returned
- it cannot name operator error as a root cause
- it cannot take any action — every record waits on a human

---

# Appendix B — Google Cloud integration, step by step

Everything in **`asia-south1`**, project `d-copilot-2026`.

## Services, and what each one carries

| Service | Role | Where |
|---|---|---|
| **Vertex AI — Gemini 2.5 Flash** | Every generation and vision/audio call | `tools/llm.py` — the only place a client is constructed |
| **Vertex AI — text-embedding-005** | 768-dim vectors for quality memory and document search | `tools/llm.py`, `tools/memory.py` |
| **Vertex AI RAG Engine** | Corpus over the PFMEA, control plan and past 8Ds | `tools/doc_search.py`, `infra/build_rag.py` |
| **BigQuery** | 64 lots, 9 process parameters each, maintenance log, CAPA history | `tools/plant_data.py` |
| **Firestore (Native)** | Investigations, events, CAPA, holds, work orders, and the memory vector index | `state.py` |
| **Cloud Storage** | Defect photos, generated charts, quality documents | `tools/storage.py` |
| **Cloud Run** | The FastAPI service, min-instances 1, 300s timeout for SSE | `backend/Dockerfile` |
| **Firebase Hosting** | The React app | `firebase.json` |

## How it was set up

1. **Project and APIs** — `d-copilot-2026`, with Vertex AI, BigQuery, Firestore, Cloud Storage, Cloud Run, Cloud Build, Artifact Registry, Secret Manager and Firebase enabled.
2. **Model selection, by testing not by reading** — Model Garden *lists* several Gemini 3.x Flash models, but every one returns 404 for this project. `gemini-2.5-flash` was the only Flash that answered. Region chosen because both it and RAG Engine work there.
3. **BigQuery** — `infra/load_data.sh` creates the `plant` dataset and loads lots, process, maintenance, complaints and CAPA history, idempotently.
4. **Firestore** — native mode, plus a composite vector index on the memory collection at **dimension 768**, measured from the embedding model rather than assumed.
5. **RAG corpus** — `infra/build_rag.py` uploads the quality documents and imports them. Uses the current `agentplatform` client; `vertexai.rag` is deprecated.
6. **Cloud Storage** — `d-copilot-2026-assets`, holding images, documents and charts.
7. **Cloud Run** — built from `backend/Dockerfile`, env-configured, running as the project's compute service account with `aiplatform.user`, `bigquery.dataViewer`, `bigquery.jobUser`, `bigquery.readSessionUser`, `datastore.user` and `storage.objectAdmin`.
8. **Firebase Hosting** — serves the SPA. The app calls Cloud Run directly rather than through the `/api/**` rewrite, because Firebase's CDN buffers SSE and would deliver the live trace in one burst at the end.

## Two decisions worth defending

**No API key anywhere.** The service authenticates as itself through Vertex AI;
locally it uses Application Default Credentials. Nothing to leak into a public
repo. A grep for `AIza` across the codebase returns nothing.

**Every backend is swappable by environment variable.** `PLANT_BACKEND`,
`STATE_BACKEND`, `DOCS_BACKEND` and `FILES_BACKEND` each select between a local
and a cloud implementation behind one interface. A fresh clone runs offline; the
deployment runs entirely on Google Cloud. The same CAPA returns the same verdict
either way — verified.
