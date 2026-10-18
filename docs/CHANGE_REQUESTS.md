# Change requests — round 1

Raised by Sabari after walking the deployed app at `https://d-copilot-2026.web.app`.
More are expected; this file is the running list.

Status key: **open** · **in progress** · **done** · **needs a decision**

---

## 1. Remove the "New" tab — open

The sidebar and bottom bar list `Inbox · New · Memory`. "New" opens
`/new` with no complaint, where the screen offers *"No complaint selected — fill in
the details manually."*

That reads as **Priya filing a complaint**, which is not her job. Customers raise
complaints; she receives and investigates them. An investigation with no complaint also
has no customer, no product and no due date, so the *"8D due in N working days"*
countdown — the thing driving urgency in the whole story — has nothing to count toward.

**Change:** drop "New" from `NAV_ITEMS` (leaving `Inbox · Memory`). Keep the `/new`
route, since the inbox navigates to it with `?complaint=…`. Redirect to the inbox if it
is reached without one. Retitle the screen to name the complaint it belongs to.

**Not affected:** the live photo upload stays. Complaints are text only — the customer
describes the defect, Priya photographs the returned board herself, which is what a
quality engineer actually does. Losing live upload would have invited "is the AI really
looking at that image?", the one question this product exists to answer.

---

## 2. Label AI-generated content — open

Wherever the model produced something, say so.

**Important refinement:** do *not* put a blanket "AI generated" banner on everything. The
product's central claim is that the AI does **not** decide. Labelling a verdict as
AI-generated would actively undermine the thing being judged.

| Element | Label |
|---|---|
| Defect type, severity, bounding box | AI — Gemini vision |
| Hypothesis text | AI-proposed |
| 8D sections D1–D8 | AI-drafted · edit before approving |
| Japanese / English customer reply | AI-drafted |
| **Verdicts, p-values, effect sizes** | **Computed from lot data** — not AI |
| Citation quotes | Quoted from *(source document)* |

Done properly this becomes the strongest visual argument in the product: a judge seeing
*"Supported · computed from lot data, Welch t-test p = 0.0002"* beside *"8D draft ·
AI-drafted, edit before approving"* can **see** the division of labour instead of being
told about it.

---

## 3. Back navigation — open

Confirmed by inspection: `Evidence.tsx` and `Done.tsx` have **no navigation out at all**,
and `Review.tsx` only moves forward (to `/done`). Once a judge clicks "See the evidence"
the browser back button is their only escape.

**Change:** add a back link on Evidence, Review and Done — back to the investigation,
plus a route home to the inbox.

---

## 4. Progress indication during AI steps — open

Show that work is happening while a model call is in flight: a loading state reading
something like *"AI is generating answers"*, on the steps that wait on Gemini.

Worth pairing with the §2 labelling so the wording matches: the live trace already names
each agent as it starts, so this is about the gap *between* events, where the screen is
currently silent. Vision alone has taken up to 22 s.

---

## 5. Remove the "Synthetic demo data" footer — DONE (decided: remove entirely)

Requested: remove *"Synthetic demo data · Built with Gemini on Google Cloud"* from the
footer.

**Concern, raised once and then I'll do whatever is decided.** The PRD mandates it
(§13, Honesty: *"'Synthetic demo data' label on every screen"*), and it is part of the
prepared answer to §17's *"you planted the cause — it's theatre"*. Openly labelling the
data is what makes the planted-cause demo defensible rather than suspicious. A judge who
discovers the data is synthetic **after** being told it was real reacts very differently
from one who was told up front.

**Middle options, if the footer is simply too prominent:**
- keep the line but make it quieter — smaller, lower contrast
- show it on the Inbox and Done screens only, not all seven
- reword to something less apologetic, e.g. *"Demo plant data · Built with Gemini on
  Google Cloud"*
- drop it from the UI but keep it loud in the README and on the deck's data slide

**Decision taken (18 Oct).** First pass moved the wording to a quiet header chip reading
"Demo data". The owner then asked for that gone too, so the wording is now absent from
every screen. The honesty claim lives in three places that remain: the plant name reads
*"Sree Electronics (fictional), Chennai"* in the header of every screen, the README states
it plainly, and the deck's data slide says it out loud.

`AppShell.test.tsx` asserts no demo-data wording survives anywhere in the shell, so the
chip cannot creep back in. CLAUDE.md rule 5 was updated to match — it previously required
a UI label and would otherwise have read as a standing instruction to restore it.

---

## 6. Five open complaints in the inbox — open

Currently `complaints.csv` holds three rows: two open (`C-2026-031` solder bridging,
`C-2026-032` tombstoning) and one closed (`C-2026-024`).

**Change:** add rows so five are open. Needs realistic customers, products, lots, defect
types and due dates consistent with the existing plant data. `C-2026-031` must stay the
golden path.

---

## 7. Sort complaints by date — open

Order the inbox by date. Decide and state the direction — newest first is the usual
inbox convention; due-date order is arguably better for a quality engineer working to
deadlines. Possibly: open complaints by due date ascending (most urgent first), closed
ones below.

---

## 8. Navigation between received complaints — open

Allow moving between complaints from within one, rather than returning to the inbox each
time — previous/next, or a list rail beside the detail.

---

## Notes

- `C-2026-031` is the demo's golden path and must keep working end to end.
- The live upload path must survive every change here.
- Each change needs its tests updated and a redeploy; the deployed bundle and the repo
  must not drift.

---

# Change requests — round 2

Raised after an internal team review of the deployed prototype.

---

## 9. Make the existing AI work visible — open · HIGH PRIORITY

**The actual problem.** The internal review concluded there is "less integration with
the AI". The product in fact uses eight distinct Gen AI capabilities — multimodal vision,
schema-validated structured output with retry, agentic hypothesis generation across the
6Ms, tool use where statistics override the model, RAG with row-level citations,
embeddings with vector search, grounded long-form writing with a number-provenance check,
and bilingual generation with keigo register control.

None of that is visible in the UI, so it reads as "upload a photo, get a draft". **This
is a presentation gap, not a capability gap**, and fixing it is worth more than building
anything new.

**Change:** while an answer is being generated, show what is actually happening — name
the capability in flight, not just the agent. "Reading the defect photo (Gemini vision)",
"Searching the PFMEA and control plan (vector search over 48 passages)", "Testing H2
against 64 lots (Welch t-test)", "Checking every number against tool results".

Pairs with change #2 (precise AI vs computed labelling) and #4 (progress during model
calls). Together these three are the single highest-value piece of work outstanding.

---

## 10. Mobile responsive — open

Reported as not behaving on mobile. Note that 390 px was a PRD MUST and was verified
during the build, so this is likely a regression or a specific screen rather than a
wholesale gap. **Audit every screen at 390 px before changing anything** — find what
actually broke rather than rewriting layouts that work.

---

## 11. Show the model's reasoning — approved

Gemini 2.5 supports thinking budgets and thought summaries. Surface the investigator's
reasoning as it decides which of the 6Ms to pursue, so the live trace shows a colleague
thinking rather than a black box.

---

## 12. Voice note intake — approved

A shift lead records a note; the agent extracts it as evidence. Gemini handles audio
natively and supports Tamil (`ta-IN`) and Hindi (`hi-IN`).

Strategic value: a second input modality, and it hardens the "a Tier-2 plant has no MES"
answer from "it reads their spreadsheet" to "it reads a voice note from the floor".

---

## 13. CAPA effectiveness verification — explained, not yet approved

When a new defect matches a past CAPA in quality memory, run the statistics on lots
produced **after** that CAPA was implemented and answer: did it work? Three outcomes —
it worked; it never worked; it worked then regressed.

Addresses the PRD's own opening complaint ("the same defect returns next quarter") and
the gap industry research names as the real one: recurrence rate, not CAPA count, is the
measure of a working system.

**State:** roughly 60% of the parts exist (memory carries CAPA ids, the statistics engine
works, lots carry dates). None of the feature exists — no comparison logic, no agent step,
no UI.

---

## 14. Rejected-8D complaints in the inbox — approved

Two of the five open complaints (#6) should be **customer rejections of a previously
submitted 8D**, rather than new defect reports. Priya opens one, the agent reads what the
customer objected to, and revises the 8D.

This is the PRD's opening pain made literal: *"the 8D gets sent back"*. Needs the rejected
8D and the customer's objection as data, plus an agent step that revises rather than
drafts from scratch.

---

---

# Change requests — round 3

Raised while preparing the submission (URL + deck + screen recording), thinking about
what a judge will actually do with the link.

---

## 15. Live microphone capture, not a file upload — DONE

A judge will not have a `.wav` of a shift lead to hand. The voice note had to be
something they can *do*: press the mic, talk, press it again.

**Built:** one toggling button. Click to record — pulsing indicator, elapsed timer,
"Recording". Click again — "Transcribing with Gemini…" — then the transcript panel:
the transcript in whatever language was spoken, an English translation when it differs,
the lot or line it heard, the observations and maintenance mentions it extracted, and a
warning naming any field it is not sure it heard.

New endpoint `POST /api/voice/transcribe`, a deliberate dead end: it starts no
investigation and writes no state. The recorded blob is still posted with the
investigation, which **re-reads the audio server-side** rather than trusting a
client-supplied extraction — one extra model call, bought on purpose (CLAUDE.md rule 4).

**Two things found by testing rather than assuming:**

- Safari records `audio/mp4`, which is not in Gemini's accepted list; `audio/m4a` is the
  same container under a name it knows. Without that mapping, live recording would have
  failed on every iPhone and Mac. Verified against the deployed service with a real
  AAC-in-MP4 file.
- A permission prompt that is *dismissed* rather than answered leaves `getUserMedia`
  pending forever. The Record button sat disabled with no way back. The wait is now
  bounded, and a file picker appears once the mic has failed, so someone who blocked the
  permission outright can still use the feature.

Verified end to end against `https://d-copilot-2026.web.app` with a real browser and a
fake capture device: record → indicator → stop → transcribing → transcript.

---

## 16. Will a judge's own photo work? — DONE (one real gap, fixed)

The honest answer, checked rather than assumed:

- **Yes, the read is genuinely theirs.** The vision call sends their bytes to Gemini.
  Nothing is cached, keyed to a filename, or pre-baked.
- **A photo that is not a defective board returns `none`** and the app says so —
  "no defect visible, escalate to physical inspection" — instead of inventing one. That
  path is decided by Python, not the model.
- **The gap, now fixed:** Gemini accepts only PNG, JPEG, WEBP, HEIC and HEIF. A GIF, BMP
  or TIFF — all reasonable things to try — failed the whole investigation.
  `vision_tool` now re-encodes anything outside that list to JPEG. Verified live: a BMP
  of the demo board reads `solder_bridge · critical`, same as the JPEG.

**The limit worth stating out loud in the deck, because a judge will find it:** the
*statistics* always run against the complaint's lot in the plant dataset, not against
their board. We have no process data for their photo — no reflow temperatures, no AOI
counts. So the defect reading is theirs; the root-cause analysis is still Sree
Electronics'. That is a property of not having their plant's data, not a shortcut.

---

---

## 17. Drop "(fictional)" from the chrome, and make the complaints dropdown two views — DONE

**Two separate asks, both done.**

### The "(fictional)" qualifier

Out of the top bar and out of the complaints sidebar. Done via one display-layer helper,
`frontend/src/api/display.ts`, applied at every place a customer or plant name is
rendered — header, sidebar, both complaint lists, the investigation heading and the
prev/next complaint links. Partial removal would have read as a bug rather than a
decision.

**The data is untouched.** `data/constants.py` still spells the names
`Hoshino Denso (fictional)`, so BigQuery still carries them, and the 8D a judge reads
still quotes the customer exactly as the record spells it. Nothing downstream of a tool
result is being quietly rewritten to look better — the stripping happens at render and
nowhere else. The honesty claim lives in the README and the deck's data slide, same
decision as CR #5.

### The complaints dropdown

It previously spilled every open complaint and every past investigation into the
sidebar, which turned a navigation control into a second copy of the page it navigates
to. It now lists exactly two entries — **Open complaints** and **Past investigations** —
each with a count, each opening that list in the main section.

`/complaints` is the open list; `/complaints?view=past` is the past one. A query param
rather than a second route, so an unrecognised or stale value falls back to the open
list — the screen's primary job — instead of erroring. The dropdown now starts expanded,
since two short entries cost nothing to show.

The KPI strip (soonest 8D due, rejections outstanding) stays with the open list only;
those numbers are meaningless over closed rows.

### Found while verifying: the deployed BigQuery table was stale

The five extra past investigations added in round 2 (CR #6's sibling) existed in
`data/out/complaints.csv` and passed the backend test, but **had never been loaded into
BigQuery** — the deployed app was serving 6 complaints where the dataset has 11, so
"Past investigations" read 1 instead of 6. Reloaded with `bq load --replace`; the live
API now returns 5 open and 6 closed.

Worth remembering as a class of bug: the backend tests run against the CSV backend, so
they cannot see a stale cloud table. A green test suite is not evidence that the
deployment has the same data.

### Minor, not a defect

`/api/capas` takes ~5 s because it computes effectiveness statistics per CAPA, so the
CAPA links on the past-investigations rows appear a few seconds after the rows do. Fine
in use; worth knowing before recording the screen.

---

---

## 18. Tab switching was slow — DONE (8.7 s → 0.03 s)

**Measured first, then fixed.** Server-side timings before:

| Endpoint | Before | After |
|---|---|---|
| `/api/dashboard/summary` | 8.7 s | 0.23 s |
| `/api/capas` | 7.5 s | 0.19 s |
| `/api/plant/maintenance` | 1.2 s | 0.10 s |
| `/api/complaints` | 1.0 s | 0.09 s |

### The cause: reads per *item*, not per request

`plant_data._joined_cached()` cached the lots+process join, but `capa_lots()`,
`complaints()` and `maintenance()` were uncached — and under `PLANT_BACKEND=bigquery`
every one of those is a network round trip. `get_capa_lots()` is called **once per
CAPA** by `list_capas_with_effectiveness()`, so listing 8 CAPAs issued **8 identical
`SELECT * FROM capa_lots` queries**. The dashboard does that same work plus a complaints
read, which is why it was the slowest screen in the product.

These are static reference tables — they change when `infra/load_data.sh` runs `bq
load`, a deploy-time action, never a request-time one. `_table_cached` now caches them
for the life of the process, the same decision `_joined_cached` already made about
lots+process. `_table()` copies outside the cached function so one caller's in-place
mutation cannot poison the next — the bug that split `joined()`/`_joined_cached()`
originally.

### Three layers, so the cost is paid nowhere a user can see it

1. **Backend cache** — the fix above.
2. **Startup warm** (`warm_plant_cache()`, called from the app lifespan) — pulls every
   table in while nobody is waiting, so even the first request after a cold start is
   fast. Without it the first visitor paid ~5 s.
3. **Frontend cache + prefetch** (`client.ts`) — each tab fetches on mount, so revisits
   re-paid the round trip. Reads are now cached by path, and `prefetchAll()` warms all
   six in the background as soon as the shell mounts. The cache holds the *promise*, so
   the sidebar and the page asking at the same moment share one request rather than
   racing two. A rejected entry is dropped, so a transient 503 doesn't look like a
   permanently broken tab.

**Invalidation:** approving is the only thing that changes any of this (it creates a
CAPA, a hold and a memory entry), so `approve()` clears the cache on the way out.
`getInvestigation` is deliberately **not** cached — the live screen polls it while the
run progresses, and caching would freeze it at `running` forever.

### Measured in a real browser, click to content on screen

| Tab | First visit | Revisit |
|---|---|---|
| Dashboard | 813 ms | 62 ms |
| Complaints | 34 ms | 27 ms |
| CAPA | 36 ms | 33 ms |
| Memory | 31 ms | 35 ms |
| Plant | 41 ms | 32 ms |

The Dashboard's first visit is chart rendering, not data.

---

## 19. Two near-identical open CAPAs — leftover demo state, not a code bug

`CAPA-0142` and `CAPA-0143` differ only by date. They came from **two separate
investigations of the same complaint** — `inv_8de98e06` (18 Oct) and `inv_66882e7e`
(17 Oct), both of complaint `C-2026-033` / lot `L2612`, both approved. Each approval
correctly created its own CAPA and its own memory entry (`MEM-0001`, `MEM-0002`). The
code did exactly what it should; the records are accumulated test state in Firestore.

**Resolved by explaining it in the UI rather than deleting the records.** Each affected
card now carries a note: *"Investigation 2 of 2 on complaint C-2026-033. Not a duplicate:
the same complaint was investigated more than once and each approval opens its own CAPA.
This one came from inv_8de98e06 on 2026-10-18. The other is CAPA-0143 (2026-10-17)."*

Explaining beats hiding here. Two identical open CAPAs read as a duplicate-detection
failure — the worst possible misread for a product whose pitch is that quality memory
stops recurrence — and a judge who asks about them now gets the answer on screen.

The note is **computed from the records**, not hard-coded to this pair: it groups by
`complaint_id`, numbers each card by date, links to its siblings, and disappears on its
own once there is one CAPA per complaint. `siblingsOnSameComplaint` is exported and
tested separately, because the grouping — not the wording — is what has to stay true.

**The real gap it exposes, worth naming rather than fixing today:** nothing stops the
same complaint being investigated twice and opening a second CAPA for it. A product
claiming to manage recurrence should notice an open CAPA on the same complaint, lot and
defect type and offer to amend it rather than silently opening another. Named here as a
deliberate gap, not an oversight.

---

## Scope note — written down deliberately

Approved across both rounds: 8 UI changes, mobile audit, reasoning visibility, voice note
intake, rejected-8D complaints. Realistically a full day, against a submission tomorrow
that still needs a video and a deck.

Build in priority order, each piece shippable on its own, so whatever is reached is
working rather than half-done. Priority: **9 + 2 + 4 (visibility) → 1 + 3 (navigation and
persona) → 6 + 7 + 8 (inbox) → 11 (reasoning) → 12 (voice) → 14 (rejections)**.

Estimates given in conversation are build time including tests, review and redeploy —
and have been consistently optimistic today. Treat them as floors.
