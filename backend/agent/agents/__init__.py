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

**This exemption list is conditional on the local backends, not permanent.** The
"doesn't need it" calls above — `get_lot_genealogy`/`get_process_window`/
`get_maintenance_events`/`get_comparison_groups` in `agent/tools/plant_data.py`, and
`agent/tools/storage.put_bytes` (used by the chart tool) — are fast and local only
because this project currently runs `PLANT_BACKEND=csv` and `FILES_BACKEND=local`. Flip
either to its cloud form (`bigquery`, `gcs`) and the exact same call sites become real
network I/O made synchronously from inside an `async def` agent — the same event-loop
freeze this file exists to prevent, reintroduced silently by a config change rather than
a code change. Before flipping either selector in a task that talks to the real backend,
re-measure call latency under load and thread whichever calls turn out slow enough to
matter; do not assume the exemption still holds.

The highest-risk one is NOT in this package at all: `agent/events.py`'s `EventBus.publish`
calls `get_state().append_event(inv_id, event)` synchronously, on every single published
event, with no exemption review of its own because it was written against
`STATE_BACKEND=memory`. Flip `STATE_BACKEND` to `firestore` and every `bus.publish` —
which is to say every step of every agent, several times each — becomes a Firestore
write on the event loop, on the exact SSE path this task exists to keep responsive. A
later task that turns on the cloud backends must treat this one as the first thing to
measure, not an afterthought.
"""
