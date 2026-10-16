"""One agent per file. Each publishes events; none of them knows about HTTP.

Threading convention (task 10 fix — read this before adding a new agent, including
`actions.py`): `agent/tools/llm.py`'s `generate_structured`, `generate_text` and `embed`
are plain synchronous functions that block on a real network call to Gemini. uvicorn
runs a single-threaded asyncio event loop, so calling any of them directly from an
`async def` agent freezes the ENTIRE server — every other request, including the SSE
event stream itself — for the duration of that call, not just this investigation's own
pipeline (measured: a concurrent `GET /api/health` took 59 s during one investigation
run, before this fix).

The fix is NOT to make the tools async — their signatures stay synchronous on purpose, so
scripts and tests that call them directly keep working unchanged. Instead, every call site
*inside this package* wraps the blocking call in `asyncio.to_thread(...)`:

    result = await asyncio.to_thread(generate_structured, prompt, Schema)

Any tool that makes a network call (an LLM call, an embedding call, and therefore
anything built on `search_quality_memory` or `search_quality_docs`, which embed under
the hood) must be called this way from async agent code. Local, in-memory computation
(`test_hypothesis`'s stats, `parse_lot_traveler`'s openpyxl parse) does not need it — the
thread hop would cost more than the blocking call itself. See `vision.py`, `intake.py`,
`investigator.py`, `evidence.py` and `writer.py` for the pattern; `actions.py` (not built
yet) will call `generate_structured` for the bilingual customer reply and must follow the
same convention.

**Update (task 14 — the cloud backends are now live).** The paragraph above used to read
"this exemption list is conditional on the local backends, not permanent" as a warning
for whoever flipped `PLANT_BACKEND`/`FILES_BACKEND`/`STATE_BACKEND` next. That task has
now happened, and the exemption no longer holds, by design: every call site that becomes
real network I/O under a cloud backend is threaded the same way the model calls are.

- `get_lot_genealogy`, `get_process_window` and `get_maintenance_events`
  (`agent/tools/plant_data.py`), called from `agent/agents/investigator.py`, are
  threaded there. `test_hypothesis` (`agent/tools/stats_test.py`) is threaded at its
  call site in `investigator.py` too: it calls `get_maintenance_events` for event
  hypotheses and `render_reflow_chart` -> `agent.tools.storage.put_bytes` for the
  chart, either of which is a network call once `PLANT_BACKEND=bigquery` /
  `FILES_BACKEND=gcs`.
- `agent.tools.storage.put_bytes` is also threaded at its other call site, the photo
  upload in `agent/orchestrator.py:start`.
- `get_comparison_groups` and the `_propose_actions` helper (which calls
  `get_lot_genealogy`) are threaded at their call sites in
  `agent/orchestrator.py:run_investigation`.
- `agent/events.py`'s `EventBus.publish` — the highest-risk one, since it runs on
  every single published event regardless of which agent is working — now wraps
  `get_state().append_event(...)` in `asyncio.to_thread` too, so `STATE_BACKEND=firestore`
  does not turn every event into a blocking Firestore write on the SSE path.
- `search_quality_docs` (`agent/tools/doc_search.py`), called from
  `agent/agents/evidence.py`, was already threaded before this task because it always
  embeds the query — `DOCS_BACKEND=vertex` needed no new threading.

Measured before/after latency for each flip is in the task 14 report
(`.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-14-report.md`). If a future
change adds a new call to a `*_BACKEND`-selected tool from async agent code, thread it
the same way — do not assume a CSV/local/in-memory backend's speed generalizes to its
cloud counterpart.
"""
