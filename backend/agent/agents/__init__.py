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
"""
