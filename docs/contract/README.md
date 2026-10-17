# 8D Copilot API contract

Authoritative. Supersedes the four-endpoint sketch in `8D_Copilot_Team_Playbook.md` §4.
Any change needs both the backend and UI owner to approve the pull request.

Base: `{API_URL}/api`

1. `GET /complaints` → list of complaints with parsed fields and due-date countdown.
   Sorted by `due_in_working_days` ascending (most urgent first), open complaints
   before closed ones (CR #7) — the client renders them in the order received rather
   than re-sorting. Two fields distinguish a customer's rejection of an
   already-submitted 8D from a new defect report (CR #14): `is_rejection: bool` and
   `objection: str` (the customer's stated reason, e.g. "root cause stated as operator
   error; not acceptable", empty for a new complaint). A rejection also carries
   `original_eight_d`: the full `EightD` shape (`D1..D8: {text, citations[]}`) of the
   8D being rejected, or `null` for a non-rejection. Starting an investigation against
   a rejection (`POST /investigations` with that `complaint_id`) runs the revise path
   (`agent="reviser"` events, see below) instead of drafting from scratch.
2. `POST /investigations` (multipart: `image`, `complaint_id`, `complaint_text`, `lot_id`, optional `traveler` xlsx) → `{ "id": "inv_123", "status": "running" }`
3. `GET /investigations/{id}/events` (SSE). Each event:
   ```json
   { "seq": 4, "ts": "2026-10-16T10:02:11Z",
     "agent": "intake | vision | investigator | evidence | writer | reviser | system",
     "type": "step_started | tool_call | tool_result | memory_hit | hypothesis | hypothesis_result | citation | draft_ready | done | error | capa_effectiveness",
     "title": "Testing: reflow peak temperature drift on Line 2",
     "detail": "Welch t-test, defect lots vs good lots",
     "data": {} }
   ```
   `hypothesis_result.data`: `{ "hypothesis_id": "H2", "verdict": "supported|rejected|inconclusive", "p_value": 0.003, "effect": "+8.1 °C mean peak temp", "n_defect": 6, "n_good": 58, "chart_url": "..." }`

   `capa_effectiveness.data` (`CapaEffectiveness`, `agent/tools/capa_check.py`): emitted by the investigator immediately after a `memory_hit` whose entry carries a usable `capa_id` and `line` — "similar past case found" is not the same claim as "that case's fix worked", and this is the event that answers the second question, with the same statistical rule (`agent/tools/stats_verdict.classify`) that decides every other verdict in this product. Not every `memory_hit` gets one: a hit with no `capa_id` (nothing was raised against that past cause) or no `line` emits no `capa_effectiveness` event at all.
   ```json
   { "capa_id": "CAPA-0098", "defect_type": "tombstoning", "line": "L1",
     "implemented_on": "2026-07-10", "verdict": "worked | never_worked | regressed | insufficient_data",
     "test": "Welch t-test", "p_value": 0.4816, "effect": "1.8% right after CAPA-0098, barely moved from 2.0% before it (p=0.4816) -- signed off, never actually fixed",
     "effect_value": -0.0019, "effect_unit": "defect rate",
     "n_before": 10, "n_immediate": 7, "n_recent": 7,
     "group_labels": ["Before CAPA-0098 (implemented 2026-07-10)", "Immediately after CAPA-0098", "Recent, after CAPA-0098"],
     "before_rate": 0.02, "immediate_rate": 0.0182, "recent_rate": 0.014,
     "p_immediate": 0.4816, "p_recent": 0.0545, "chart_url": null }
   ```
   `reviser` events (CR #14): when the complaint behind an investigation is a rejection
   (`Complaint.is_rejection`), the orchestrator runs `agent/agents/reviser.py` instead
   of `agent/agents/writer.py` after the evidence step. It is a distinct agent name
   (not a flag on `writer`'s events) precisely so the live trace shows "revising the 8D
   against the customer's objection" as its own step, separate from drafting one from
   nothing — the same `step_started`/`draft_ready` event types as the writer, under
   `agent: "reviser"`. It is handed the rejected `original_eight_d`, the customer's
   `objection`, and the SAME test results/citations a fresh draft would use; it must
   never carry forward "operator error" as a root cause, and the number-provenance
   check (`agent/tools/provenance.py`) runs on its output exactly as it does on the
   writer's.

   `verdict` is a four-way, CAPA-specific vocabulary (distinct from `hypothesis_result.verdict`'s `supported|rejected|inconclusive`) because "did this fix work" has an honest fourth answer a single significance test cannot express: `worked` (the rate dropped and stayed down), `never_worked` (no significant, meaningful drop — including a rate that rose, which is never "worked" however significant), `regressed` (it dropped, then climbed back), `insufficient_data` (too few lots on one side to say anything — never guessed). `p_value`/`effect_value`/`effect` carry whichever comparison decided the verdict (before-vs-immediate for `never_worked`, before-vs-recent for `worked`/`regressed`); `p_immediate`/`p_recent` are always both present except for `insufficient_data`, where every numeric field is `null`.
4. `GET /investigations/{id}` → full state: `status` (`running | draft_ready | approved | insufficient_evidence | failed`), `defect {type, severity, box[x,y,w,h], confidence, visual_evidence}`, `hypotheses[]`, `eight_d {D1..D8: {text, citations[{label, source, ref}]}}`, `proposed_actions[{id, kind: capa|hold|work_order|customer_reply, summary}]`. `failed` means the run raised an exception before reaching a verdict; `missing_data[0]` carries the error message, and the event stream still ends `error` then `done` — a client polling this endpoint must stop on `failed` rather than spin forever.
5. `POST /investigations/{id}/approve` body `{ "approver": "Priya R.", "edits": {"D4": "..."}, "rejected_action_ids": ["A3"], "note": "..." }` → `{ "capa_id", "hold_id", "work_order_id", "replies": {"ja", "en"}, "memory_id", "rejected_action_ids" }`. The response echoes back `rejected_action_ids` (same ids the request sent) so a client can tell "excluded at review" apart from "attempted and failed" — `replies` is null in both cases (the customer-reply Gemini call degrades to null on failure rather than raising), and only membership in the echoed `rejected_action_ids` proves which one happened.
6. `GET /memory` → saved confirmed causes.
7. `GET /health` → `{ "ok": true, "model": "<GEMINI_MODEL>" }`

Commit `mock_events.json` (21 events for the golden path) and `mock_investigation.json` so the UI can be built with `VITE_USE_MOCKS=true` (replay one event every 600 ms).

The table below lets the UI switch on `type` exhaustively:

| `type` | emitted by | `data` |
|---|---|---|
| `step_started` | any | `{}` |
| `tool_call` | any | `{"tool": "...", "args": {...}}` |
| `tool_result` | any | `{"tool": "...", "summary": "..."}` |
| `memory_hit` | investigator | `MemoryEntry` |
| `capa_effectiveness` | investigator | `CapaEffectiveness` (only when the preceding `memory_hit` carries a `capa_id` and `line`) |
| `hypothesis` | investigator | `Hypothesis` |
| `hypothesis_result` | investigator | `HypothesisResult` |
| `citation` | evidence | `Citation` |
| `draft_ready` | writer \| reviser | `{"status": "draft_ready" \| "insufficient_evidence"}` — `reviser` only for a rejection complaint (CR #14) |
| `done` | system | `{}` |
| `error` | system | `{"message": "..."}` |
