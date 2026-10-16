# 8D Copilot API contract

Authoritative. Supersedes the four-endpoint sketch in `8D_Copilot_Team_Playbook.md` §4.
Any change needs both the backend and UI owner to approve the pull request.

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
4. `GET /investigations/{id}` → full state: `status` (`running | draft_ready | approved | insufficient_evidence | failed`), `defect {type, severity, box[x,y,w,h], confidence, visual_evidence}`, `hypotheses[]`, `eight_d {D1..D8: {text, citations[{label, source, ref}]}}`, `proposed_actions[{id, kind: capa|hold|work_order|customer_reply, summary}]`. `failed` means the run raised an exception before reaching a verdict; `missing_data[0]` carries the error message, and the event stream still ends `error` then `done` — a client polling this endpoint must stop on `failed` rather than spin forever.
5. `POST /investigations/{id}/approve` body `{ "approver": "Priya R.", "edits": {"D4": "..."}, "rejected_action_ids": ["A3"], "note": "..." }` → `{ "capa_id", "hold_id", "work_order_id", "replies": {"ja", "en"}, "memory_id" }`
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
| `hypothesis` | investigator | `Hypothesis` |
| `hypothesis_result` | investigator | `HypothesisResult` |
| `citation` | evidence | `Citation` |
| `draft_ready` | writer | `{"status": "draft_ready" \| "insufficient_evidence"}` |
| `done` | system | `{}` |
| `error` | system | `{"message": "..."}` |
