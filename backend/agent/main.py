"""FastAPI surface. docs/contract/README.md is the agreement — change both sides together."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent.config import get_settings
from agent.events import TERMINAL, bus
from agent.orchestrator import format_error_message, run_investigation, start
from agent.state import get_state
from agent.tools.intake_tools import list_complaints
from agent.tools.memory import list_quality_memory, seed_historical_quality_memory
from agent.tools.storage import get_local_path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once, before the server accepts any request -- not per-request, so this is
    the one place in the codebase a blocking embedding call is NOT routed through
    asyncio.to_thread (see agent/agents/__init__.py): nothing is waiting on the event
    loop yet. Degrade, don't explode: a demo that starts with no quality-memory history
    (e.g. no embedding credentials in a bare dev environment) must still serve every
    other route, the same "best-effort" posture agent/agents/actions.py already uses
    for the customer-reply and quality-memory calls on the approval path."""
    try:
        seed_historical_quality_memory()
    except Exception as exc:
        log.warning("historical quality-memory seed failed: %s", exc.__class__.__name__)
    yield


app = FastAPI(title="8D Copilot API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


@app.middleware("http")
async def require_demo_code(request: Request, call_next):
    """Gate every /api/* route except /api/health behind DEMO_ACCESS_CODE — the
    deployed demo runs with --allow-unauthenticated, so this is the only thing
    standing between the Cloud Run URL and a stranger. /api/health stays open so a
    judge (or an uptime check) can see the service is alive without the code.

    Disabled entirely when DEMO_ACCESS_CODE is unset (the default) — local dev and
    the whole test suite never set it, so this must be a no-op for them.

    Browsers' native EventSource (the SSE stream) and <img>/<source> tags (the
    defect photo, the reflow chart) cannot set custom request headers, so those two
    GET-only surfaces also accept the code as a `code` query parameter. Every other
    call goes through fetch() and sends the X-Demo-Code header — see
    frontend/src/api/client.ts and frontend/src/api/demoCode.ts.

    OPTIONS is exempt unconditionally. FastAPI's `@app.middleware("http")` decorator
    calls `add_middleware`, which `insert(0, ...)`s into Starlette's middleware list
    — so this function, added AFTER `CORSMiddleware` above in source order, actually
    ends up OUTSIDE it in the call chain (runs first on the way in). A browser's CORS
    preflight is a bare OPTIONS request that never carries X-Demo-Code — that's the
    entire point of preflight, asking permission before sending the real request's
    custom headers — so without this exemption every cross-origin gated call's
    preflight was rejected here with a 401 and no CORS headers at all, before
    CORSMiddleware ever got a chance to answer it. Found live when the frontend was
    pointed at the Cloud Run origin directly (see docs/deploy notes) — same-origin
    deploys never send a preflight, so this was invisible until then. Letting OPTIONS
    through unconditionally costs nothing: the actual GET/POST that follows is still
    fully gated below.
    """
    if request.method == "OPTIONS":
        return await call_next(request)
    code = get_settings().demo_access_code
    path = request.url.path
    if code and path.startswith("/api/") and path != "/api/health":
        supplied = request.headers.get("x-demo-code") or request.query_params.get("code")
        if supplied != code:
            return JSONResponse({"detail": "missing or invalid X-Demo-Code"}, status_code=401)
    return await call_next(request)

# asyncio.create_task only keeps a WEAK reference to the task via the event loop; nothing
# else in this module holds the returned Task object, so without a strong reference
# somewhere, the task backing the one background investigation this whole API exists to
# run can be garbage-collected mid-run. Keeping it in this set until it finishes is the
# standard fix (see the asyncio.create_task docs' own warning about this).
_tasks: set[asyncio.Task] = set()


class ApproveRequest(BaseModel):
    approver: str = "Priya R."
    edits: dict[str, str] = {}
    rejected_action_ids: list[str] = []
    note: str = ""


@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "model": s.gemini_model,
            # Replay is surfaced so the UI can label it. A viewer must never be unsure
            # whether they are watching a live run.
            "replay": s.replay_case or None,
            "backends": {"plant": s.plant_backend, "state": s.state_backend,
                         "docs": s.docs_backend, "files": s.files_backend}}


@app.get("/api/complaints")
def complaints():
    return [c.model_dump() for c in list_complaints()]


@app.post("/api/investigations")
async def create_investigation(
        image: UploadFile = File(...),
        complaint_id: str = Form(""),
        complaint_text: str = Form(""),
        lot_id: str = Form(...),
        traveler: UploadFile | None = File(None)):
    inv_id = await start(
        complaint_id=complaint_id, lot_id=lot_id,
        image_bytes=await image.read(), mime_type=image.content_type or "image/jpeg",
        complaint_text=complaint_text,
        traveler_bytes=await traveler.read() if traveler else None)
    task = asyncio.create_task(_run(inv_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"id": inv_id, "status": "running"}


async def _run(inv_id: str):
    try:
        # Replay mode (REPLAY_CASE) streams a recorded run back with no model calls, so a
        # recorded demo survives a Vertex quota refusal. It announces itself in /api/health
        # and in the UI header — a viewer must never be unsure whether a run is live.
        case = get_settings().replay_case
        if case:
            from agent.orchestrator import _uploads
            from agent.replay import replay
            try:
                await replay(case, inv_id)
            finally:
                # replay() never calls run_investigation, so run_investigation's own
                # finally (which pops _uploads on the live path) never runs here.
                # start() always populates _uploads[inv_id] regardless of which path
                # _run takes, so without this pop, a full in-memory copy of every
                # replayed upload's image bytes would sit in this dict for the rest of
                # the process's life.
                _uploads.pop(inv_id, None)
            return
        await run_investigation(inv_id)
    except Exception as exc:
        log.exception("background investigation %s failed", inv_id)
        # run_investigation's own except/finally now sets status="failed" and
        # publishes "error" then "done" for every failure reachable from inside its
        # try block — which, since task 10's review, is effectively everything
        # (get_state()/get_investigation() moved inside that try too). This is a
        # backstop for genuinely unreachable cases only: something that bypasses
        # run_investigation entirely (a stub replacing it, as in the SSE contract
        # test). Without it, a subscriber would wait on the bus queue forever and the
        # SSE connection would never terminate.
        history = bus.history(inv_id)
        if not history or history[-1].type not in TERMINAL:
            message = format_error_message(exc)
            await bus.publish(inv_id, "system", "error", "The investigation could not finish",
                              detail=message, data={"message": message})
            await bus.publish(inv_id, "system", "done", "Investigation complete")
            bus.close(inv_id)


@app.get("/api/investigations/{inv_id}/events")
async def stream_events(inv_id: str):
    async def generator():
        try:
            async for event in bus.subscribe(inv_id):
                yield f"data: {json.dumps(event.model_dump())}\n\n"
        except asyncio.CancelledError:        # client navigated away
            return

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no",
                                      "Connection": "keep-alive"})


@app.get("/api/investigations/{inv_id}")
def get_investigation(inv_id: str):
    inv = get_state().get_investigation(inv_id)
    if inv is None:
        raise HTTPException(404, f"no investigation {inv_id}")
    return inv.model_dump()


@app.post("/api/investigations/{inv_id}/approve")
async def approve(inv_id: str, body: ApproveRequest):
    # Threaded (task 14 follow-up): under STATE_BACKEND=firestore this is a network
    # read, made from an async route — the same event-loop freeze risk as the model
    # calls. GET /api/investigations/{id} above stays a sync `def` (Starlette already
    # runs those off its own thread pool), so it does not need this.
    inv = await asyncio.to_thread(get_state().get_investigation, inv_id)
    if inv is None:
        raise HTTPException(404, f"no investigation {inv_id}")
    if inv.status != "draft_ready":
        raise HTTPException(409, f"investigation is {inv.status}, not draft_ready")
    # Imported here, not at module load: agent.agents.actions is Task 11's module, and
    # importing it eagerly would make every approve call 500 instead of 404/409 until
    # that module exists — the status checks above must be able to fire on their own.
    from agent.agents.actions import apply_approval
    return await apply_approval(inv, approver=body.approver, edits=body.edits,
                                rejected_action_ids=body.rejected_action_ids, note=body.note)


@app.get("/api/memory")
def memory():
    return [m.model_dump() for m in list_quality_memory()]


@app.get("/api/files/{key:path}")
def files(key: str):
    # get_local_path raises ValueError for a key that resolves outside LOCAL_DIR (a
    # path-traversal attempt, e.g. a percent-encoded "..") -- that must 404 exactly
    # like a miss, not 400, so a traversal attempt is indistinguishable from a file
    # that simply doesn't exist (no information leak about which paths are blocked).
    try:
        path = get_local_path(key)
    except ValueError:
        raise HTTPException(404, "not found")
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)
