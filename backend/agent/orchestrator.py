"""The golden path (PRD 8), in order, emitting events as it goes.

The LLM proposes, deterministic Python decides, a human approves. Nothing here forms a
verdict: the verdicts come from agent/tools/stats_test.py, and the two routes to
`insufficient_evidence` — no defect visible in the photo, and no hypothesis supported —
are both decided by Python, not by a model.
"""
import asyncio
import logging
import mimetypes
import uuid
from datetime import datetime, timezone

from agent.agents import evidence, intake, investigator, vision, writer
from agent.events import bus
from agent.models import Investigation, ProposedAction
from agent.state import get_state
from agent.tools.plant_data import get_comparison_groups, get_lot_genealogy
from agent.tools.storage import put_bytes

log = logging.getLogger(__name__)
_uploads: dict[str, dict] = {}        # inv_id -> raw bytes, kept out of the state store

NO_DEFECT_VISIBLE = ("No defect is visible in the photo. Upload a clearer image of the "
                     "reported area, or escalate to a physical inspection of the "
                     "returned units.")

# CLAUDE.md rule 6: no secrets, no image bytes, in logs or events. An SDK exception's
# str() can embed the request it was sent -- for the vision call, that payload includes
# the image bytes -- so the message that reaches the stored investigation and the
# `error` event is capped to a small prefix rather than passed through verbatim. This
# is a length bound, not a content scrub: it does not search for byte patterns, it just
# puts a fixed ceiling on how much of any single exception's text can leak.
MAX_ERROR_MESSAGE_LEN = 300


def format_error_message(exc: BaseException) -> str:
    text = f"{exc.__class__.__name__}: {exc}"
    return text if len(text) <= MAX_ERROR_MESSAGE_LEN else text[:MAX_ERROR_MESSAGE_LEN] + "…"


async def start(*, complaint_id: str, lot_id: str, image_bytes: bytes, mime_type: str,
                complaint_text: str, traveler_bytes: bytes | None = None) -> str:
    inv_id = f"inv_{uuid.uuid4().hex[:8]}"
    _uploads[inv_id] = {"image": image_bytes, "mime": mime_type,
                        "complaint_text": complaint_text, "traveler": traveler_bytes}
    # The uploaded photo itself (as opposed to the vision agent's reading of it) has to
    # be saved through the same files backend as the stats charts (agent/tools/storage.py)
    # so the UI has a URL to show it from — PRD 143: "Shown on the photo as soon as it
    # returns." `_uploads` above is in-memory and popped once the run finishes (CLAUDE.md
    # rule 6 is about not putting image bytes in logs/events, not about never persisting
    # the photo a human reviewer needs to see), so without this the UI would never have
    # anything to point an <img> at.
    ext = mimetypes.guess_extension(mime_type or "") or ".jpg"
    photo_url = put_bytes(image_bytes, f"photos/{inv_id}{ext}", mime_type or "image/jpeg")
    inv = Investigation(id=inv_id, complaint_id=complaint_id, lot_id=lot_id, status="running",
                        created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        photo_url=photo_url)
    get_state().save_investigation(inv)
    await bus.publish(inv_id, "system", "step_started", "Investigation started",
                      detail=f"Complaint {complaint_id} · lot {lot_id}")
    return inv_id


def _propose_actions(inv: Investigation) -> list[ProposedAction]:
    line = get_lot_genealogy(inv.lot_id)["line"]
    cause = next((h.text for h in inv.hypotheses
                  if h.id in {r.hypothesis_id for r in inv.results if r.verdict == "supported"}),
                 "confirmed root cause")
    return [
        ProposedAction(id="A1", kind="capa",
                       summary=f"Corrective action for {inv.defect.type.replace('_', ' ')} "
                               f"on {inv.lot_id}",
                       payload={"cause": cause, "lot_id": inv.lot_id, "line": line}),
        ProposedAction(id="A2", kind="hold",
                       summary=(f"Hold {len(inv.hold_lots)} lots: "
                                f"{inv.hold_lots[0]}–{inv.hold_lots[-1]}"
                                if inv.hold_lots else "Hold suspect lots"),
                       payload={"lots": inv.hold_lots}),
        ProposedAction(id="A3", kind="work_order",
                       summary=f"Verify and re-qualify reflow profile on Line {line[-1]}",
                       payload={"line": line, "asset": "Reflow oven",
                                "description": f"Verify and re-qualify reflow profile {line}"}),
        ProposedAction(id="A4", kind="customer_reply",
                       summary="Draft reply to the customer in Japanese and English",
                       payload={}),
    ]


async def run_investigation(inv_id: str) -> None:
    state = None
    inv = None
    try:
        # get_state()/get_investigation()/the upload lookup are inside the try, not
        # ahead of it: if any of them raised out here, the except/finally below
        # (which sets status="failed" and guarantees error-then-done) would never
        # run, leaving the investigation stuck at status="running" forever for a
        # polling client — the exact bug the "failed" status was added to close.
        state = get_state()
        inv = state.get_investigation(inv_id)
        upload = _uploads.get(inv_id, {})
        if inv is None:
            raise KeyError(f"unknown investigation {inv_id} — call start() first")

        # intake and vision read disjoint inputs (the complaint text/traveler vs. the
        # image bytes) and neither depends on the other's output, so they run
        # concurrently rather than back to back — each makes its own Gemini call, and
        # running them in sequence was summing past the PRD's 10 s "first visible
        # result" budget. Explicit Tasks (not bare coroutines passed to gather) so that
        # if one side raises, the other has a cancellable handle: asyncio.gather does
        # not cancel sibling awaitables on its own when one of them fails, so without
        # this a failing intake would leave vision's Gemini call running in the
        # background after the request that started it has already failed.
        intake_task = asyncio.create_task(intake.run(
            inv_id, upload.get("complaint_text", ""), inv.complaint_id,
            upload.get("traveler")))
        vision_task = asyncio.create_task(
            vision.run(inv_id, upload["image"], upload.get("mime", "image/jpeg")))
        try:
            (complaint, traveler_rows), defect = await asyncio.gather(intake_task, vision_task)
        except Exception:
            for task in (intake_task, vision_task):
                if not task.done():
                    task.cancel()
            # Wait for both to actually finish unwinding (cancelled or otherwise) before
            # this function's own except/finally runs, so nothing is still in flight
            # once the request that triggered it has failed. return_exceptions=True:
            # we only care that they are done, not about a second exception from the
            # task that didn't raise first.
            #
            # This guarantee covers the asyncio Task, not the OS thread underneath it.
            # Each agent's own blocking call runs via `asyncio.to_thread`, and a thread
            # pool future is NOT cancellable once started: cancelling the Task only
            # stops it resuming after that `await` returns, so the worker thread (and
            # whatever in-flight Gemini call it's running) keeps executing in the
            # background until it finishes on its own. The practical consequence is
            # benign — cancellation lands before the agent's own `bus.publish(...)`
            # call after the blocking call, so no further event can reach the stream —
            # but the thread itself is not stopped, only its result is discarded.
            await asyncio.gather(intake_task, vision_task, return_exceptions=True)
            raise

        inv.traveler_rows = traveler_rows
        inv.defect = defect
        state.save_investigation(inv)

        if inv.defect.type == "none":
            inv.status = "insufficient_evidence"
            inv.missing_data = [NO_DEFECT_VISIBLE]
            state.save_investigation(inv)
            await bus.publish(inv_id, "writer", "draft_ready",
                              "Insufficient evidence — escalate",
                              detail=inv.missing_data[0],
                              data={"status": "insufficient_evidence"})
            return

        note = " | ".join(r.remarks for r in traveler_rows if r.remarks)
        inv.hypotheses, inv.results, inv.memory_hits = await investigator.run(
            inv_id, inv.lot_id, inv.defect, note)
        inv.hold_lots = get_comparison_groups(inv.lot_id)["defect_lots"]
        inv.chart_url = next((r.chart_url for r in inv.results if r.chart_url), None)
        state.save_investigation(inv)

        inv.citations = await evidence.run(inv_id, inv)
        state.save_investigation(inv)

        out = await writer.run(inv_id, inv, complaint)
        inv.eight_d = out.eight_d
        inv.missing_data = out.missing_data
        inv.status = "draft_ready" if out.status == "draft_ready" else "insufficient_evidence"
        if inv.status == "draft_ready":
            inv.proposed_actions = _propose_actions(inv)
        state.save_investigation(inv)
    except Exception as exc:
        log.exception("investigation %s failed", inv_id)
        message = format_error_message(exc)
        # Reuse missing_data rather than add a new field: it is already the
        # Investigation's place for "why this run did not reach a verdict", shown
        # to the user, and a crash is exactly that — just undetermined earlier.
        #
        # `inv is not None` is the only guard that matters: inv can only have been
        # assigned after `state = get_state()` already succeeded, so `state` is
        # never None here when `inv` isn't. The save itself gets its own try/except:
        # if persisting the failure fails too (e.g. the same outage that caused the
        # original exception), that secondary failure must not replace or swallow
        # the investigation's own exception below — it only gets logged.
        if inv is not None:
            try:
                inv.status = "failed"
                inv.missing_data = [message]
                state.save_investigation(inv)
            except Exception:
                log.exception("investigation %s: could not persist the failed status",
                              inv_id)
        await bus.publish(inv_id, "system", "error", "The investigation could not finish",
                          detail=message, data={"message": message})
        raise
    finally:
        # The uploaded bytes never outlive the run, on either path.
        _uploads.pop(inv_id, None)
        await bus.publish(inv_id, "system", "done", "Investigation complete")
        bus.close(inv_id)
