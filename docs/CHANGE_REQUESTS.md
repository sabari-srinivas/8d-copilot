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

## Scope note — written down deliberately

Approved across both rounds: 8 UI changes, mobile audit, reasoning visibility, voice note
intake, rejected-8D complaints. Realistically a full day, against a submission tomorrow
that still needs a video and a deck.

Build in priority order, each piece shippable on its own, so whatever is reached is
working rather than half-done. Priority: **9 + 2 + 4 (visibility) → 1 + 3 (navigation and
persona) → 6 + 7 + 8 (inbox) → 11 (reasoning) → 12 (voice) → 14 (rejections)**.

Estimates given in conversation are build time including tests, review and redeploy —
and have been consistently optimistic today. Treat them as floors.
