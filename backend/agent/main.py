"""FastAPI surface. docs/contract/README.md is the agreement — change both sides together."""
import asyncio
import json
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent.config import get_settings
from agent.events import TERMINAL, bus
from agent.orchestrator import format_error_message, run_investigation, start
from agent.state import get_state
from agent.tools.intake_tools import list_complaints
from agent.tools.memory import list_quality_memory
from agent.tools.storage import get_local_path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="8D Copilot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

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
    path = get_local_path(key)
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)
