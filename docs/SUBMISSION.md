# Submission — 8D Copilot

Google Cloud AI Builder Cup 2026 · Manufacturing · JAPAC

| Deliverable | Where |
|---|---|
| Live deployed prototype | **https://q8d-copilot.web.app** — access code `demo-b1b20c` |
| GitHub repository | https://github.com/sabari-srinivas/8d-copilot |
| Demo video | *(separate deliverable)* |
| Pitch deck | *(separate deliverable — speaker notes in [`DECK.md`](DECK.md))* |
| Description | below, at three lengths |

---

## Description

### One line

8D Copilot turns a photo of a defective circuit board and a customer complaint into a
statistically tested root cause and a fully cited 8D report — where the AI proposes, the
data decides, and a human approves.

### One paragraph (~90 words)

When a customer returns defective boards, a Tier-2 electronics supplier has eight working
days to produce an 8D report naming the root cause. Today that means a quality engineer
reading spreadsheets by hand, and the guess that follows is often wrong — so the same
defect returns next quarter. 8D Copilot reads the defect photo with Gemini, proposes root
causes across the 6Ms, and then tests each one against real plant data with Welch t-tests
and Fisher exact tests. The statistics return the verdict; the model relays it, even when
it contradicts what it proposed. A human approves before anything is created.

### Full (~300 words)

**The problem.** A customer rejects a batch. Under IATF 16949 the supplier owes an 8D
report within days, naming a root cause with evidence. In a Tier-2 plant with no MES,
that means a quality engineer cross-reading shift spreadsheets under deadline. The usual
outcome is "operator error" — which closes the report and fixes nothing, so the defect
recurs. The industry's own measure of a working quality system is recurrence rate, not
how many CAPAs were raised.

**What it does.** The engineer opens a complaint, photographs the returned board, and
optionally records a spoken note from the floor. Gemini reads the photo and returns the
defect type, severity and a bounding box; it reads the audio natively, in English, Tamil
or Hindi, with no separate speech service. An investigator agent proposes three to five
hypotheses across the 6Ms, each naming exactly one measurable parameter and an expected
direction. Each is then tested in Python against 64 lots of plant data. A writer agent
drafts D1–D8 with row-level citations into the PFMEA and control plan, and a provenance
check rejects any number that did not come from a tool result. Nothing is created until a
human approves; then the system opens the CAPA, places the lot hold, raises the work
order, writes the customer reply in Japanese keigo and English, and saves the confirmed
cause to a vector-searchable quality memory — so the next similar defect starts from what
was already learned.

**The architecture, which is the point.** The model may not write a p-value, a
measurement or a verdict. It may not propose an untestable hypothesis, put an unsourced
number in the 8D, blame an operator, or take any action. One module produces verdicts,
and it is deterministic Python. In the demo, the AI's own first hypothesis is **rejected
by the statistics** — and the agent reports that rejection rather than arguing with it.

---

## Built on Google Cloud

Eight services, all `asia-south1`: **Vertex AI** (Gemini 2.5 Flash for vision, audio,
reasoning and bilingual writing; `text-embedding-005` for quality memory), **Vertex AI
RAG Engine** (citations into the quality documents), **BigQuery** (the plant dataset),
**Firestore** (investigation state and vector search over quality memory), **Cloud
Storage** (uploaded photos and generated charts), **Cloud Run** (the FastAPI backend),
**Firebase Hosting** (the React frontend), and **Cloud Build** (deploys from source).

No API key exists anywhere in this repository — the service authenticates as itself
through Vertex AI. Every backend is swappable by environment variable, so a fresh clone
runs fully offline on CSV and in-memory state, and returns the same verdicts as the
cloud deployment.

### Meeting the "Google AI models or an agentic platform" rule

The rule is an **or**, and this submission satisfies the first branch outright: **every
AI step runs Gemini 2.5 Flash through Vertex AI**. There is no second model anywhere in
the runtime — no Anthropic or OpenAI SDK is imported, and `backend/pyproject.toml` is
entirely `google-*` beside pandas, scipy and matplotlib. Antigravity, Agent Studio and
AI Studio are listed in the rules as *alternative* routes to the same requirement, not
as additional ones.

**One correction worth knowing**, since the original PRD in this repository still
describes it the old way: the agents are **not** built on Google ADK. Each is a plain
Python module calling Gemini directly through the `google-genai` SDK. ADK was evaluated
and deliberately not adopted — it was removed when it turned out to be imported nowhere.
The README says so in its own words; this note exists so the PRD's planning-stage claim
is not mistaken for a description of what shipped.

See [`DECK.md`](DECK.md) Appendix A and B for the full inventory of AI features and the
integration steps, both verified against the code rather than written from memory.

---

## What a judge should try

1. **Complaints → Hoshino Denso · C-2026-031**, upload
   `backend/data/images/defect_03.jpg`. Watch the live trace: vision, hypotheses, each
   statistical test as it returns.
2. **Press the mic** and speak a note — *"bridging again on line two, the vendor looked
   at the oven on Wednesday"*. The transcript appears in whatever language you spoke.
3. **Upload your own board photo.** The vision call is live. A photo with no visible
   defect returns *"no defect visible — escalate to physical inspection"* rather than
   inventing one.
4. **Read the Evidence screen.** Four hypotheses rejected or inconclusive, one supported.
   The rejections are the argument: a system that confirms whatever it proposes is not
   evidence of anything.
5. **CAPA tab → CAPA-0098.** A past corrective action the statistics say **never
   worked** — the recurrence question, answered with data.

**Honest limits**, stated up front and in full in the README: all plant data is
synthetic and the root cause is planted, so that the statistics have a known right
answer to find. Your uploaded photo is genuinely read, but the hypotheses are still
tested against this synthetic plant — there is no process data for your board.
