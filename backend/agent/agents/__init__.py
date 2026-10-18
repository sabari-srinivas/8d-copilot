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

**This list went through two passes.** The first pass (task 14) found the plant-data
calls in `investigator.py`, `put_bytes` and `get_comparison_groups`/`_propose_actions`
in `orchestrator.py`, and `append_event` in `events.py` — but missed every *other*
synchronous `get_state()`/plant-data call already sitting in async code elsewhere in
the same files and in `main.py`, `actions.py` and `writer.py`, because it audited "by
inspection" (file by file, reasoning about which calls looked risky) rather than
systematically. The second pass greps every call into `agent/state.py`'s `StateStore`
methods and every `agent/tools/*` function from inside an `async def` across `agent/`,
with no exceptions — the exhaustive table is in the task 14 fix report
the build report. The full,
current list:

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
- **`get_state().save_investigation(...)`/`get_investigation(...)` — eight call sites
  across `agent/orchestrator.py:start`/`run_investigation` (including the except/finally
  paths)** are threaded. These were the second pass's main find: every one of them is a
  Firestore round trip under `STATE_BACKEND=firestore`, on the same request path as
  everything else in this file.
- `main.py`'s `POST /api/investigations/{id}/approve` route threads its
  `get_state().get_investigation(...)` call. (`GET /api/investigations/{id}` and the
  other read routes stay plain sync `def`s — Starlette already runs those off its own
  thread pool, so they do not need `asyncio.to_thread`; only `async def` routes and
  agent code can freeze the *whole* loop this way.)
- `agent/agents/actions.py`'s `apply_approval` threads `state.save_investigation(...)`
  and all three `state.create_record(...)` call sites (capa/hold/work_order), alongside
  the `generate_structured`/`save_quality_memory` calls it already threaded.
- `agent/agents/writer.py`'s `run` threads `grounded_facts(...)` and
  `allowed_numbers(...)` (`agent/tools/provenance.py`) — both call
  `get_process_window`/`get_maintenance_events`/`get_lot_genealogy`/`joined` under the
  hood, a network call under `PLANT_BACKEND=bigquery`, and were missed in the first
  pass because `provenance.py` was not one of the files task 14 touched directly.
- `agent/events.py`'s `EventBus.publish` — the highest-risk one, since it runs on
  every single published event regardless of which agent is working — wraps
  `get_state().append_event(...)` in `asyncio.to_thread` too, so `STATE_BACKEND=firestore`
  does not turn every event into a blocking Firestore write on the SSE path. The
  threaded call runs **after** history/fan-out (`self._history[...].append` and
  `queue.put_nowait`), not before: two concurrent publishers against the same
  `inv_id` (intake and vision each publish their own events) must not have their
  *persistence* order determine live-delivery order — see the regression test
  `test_concurrent_publishers_deliver_in_seq_order_despite_a_slow_append_event` in
  `agent/tests/test_events.py`.
- `search_quality_docs` (`agent/tools/doc_search.py`), called from
  `agent/agents/evidence.py`, was already threaded before this task because it always
  embeds the query — `DOCS_BACKEND=vertex` needed no new threading.

Measured before/after latency for each flip is in the task 14 report
the build report. If a future
change adds a new call to a `*_BACKEND`-selected tool from async agent code, thread it
the same way — do not assume a CSV/local/in-memory backend's speed generalizes to its
cloud counterpart, and do not audit by inspection: grep for every call into
`agent/state.py` and `agent/tools/` from every `async def` in `agent/`, with no
exceptions, the way the second pass above did.
"""
