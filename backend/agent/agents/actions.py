"""What happens after a human approves. Records are created by plain code;
exactly one LLM call writes the bilingual reply (PRD 9.2).

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. `save_quality_memory` embeds under
the hood, so it goes through `asyncio.to_thread` here too, the same as
`investigator.py`'s `search_quality_memory` call. `state.save_investigation` and
`state.create_record` are threaded too (task 14 follow-up): under STATE_BACKEND=firestore
both are network calls made from this async function.

**Why `apply_approval` needs a per-investigation lock (task 14 review, round 2).**
Before that threading, the path from `main.py:approve`'s status read, through this
function's claim (`inv.status = "approved"`, persisted) and its record-creation loop,
contained zero `await` points. Single-threaded cooperative asyncio cannot interleave a
second coroutine into a stretch of code with no suspension point, so "claim before
creating anything" was an actual guarantee, not just a convention — a second concurrent
`/approve` for the same investigation simply could not run any of its own code until
the first had already persisted its claim and moved on.

Threading `save_investigation`/`create_record` put four real `await` points inside
exactly that window. `FirestoreStateStore.save_investigation`/`create_record` are plain
unconditional `.set()` calls with no compare-and-swap, so two requests that both read
`status="draft_ready"` before either commits can now both pass the guard and both
create a CAPA, a hold and a work order for one investigation — two open corrective
actions for one defect. The fix below closes that window with a per-`inv_id`
`asyncio.Lock`, re-checking the claim after acquiring it (acquiring the lock is not
enough by itself — the second caller must find out it lost, not just get its turn).

**Limitation, stated plainly:** `asyncio.Lock` serialises within one process only. It
protects every `/approve` call against every other for one investigation ID as long as
they land in the same uvicorn process. If this were ever deployed with more than one
Cloud Run instance, two instances could each hold their own, independent lock for the
same `inv_id` and still both win — the real fix there is a Firestore transaction or a
conditional write on the claim (`set status=approved only if the stored value is still
draft_ready`), not a bigger in-process lock. This project deploys with Cloud Run
`min-instances=1` and demo-level traffic, which makes the process-local lock
proportionate for now; do not assume it is airtight under a multi-instance deployment.
"""
import asyncio
import logging
from collections import defaultdict
from datetime import date

from pydantic import BaseModel

from agent.events import bus
from agent.models import Investigation
from agent.state import get_state
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.memory import save_quality_memory

log = logging.getLogger(__name__)

# Refcounted so a long-running server does not accumulate one dict entry per
# investigation ever approved. `_locks_guard` serialises mutation of both dicts: the
# "find or create, then increment" step in `_acquire_investigation_lock` spans no
# `await` by itself, but without a guard a second coroutine could still run between
# the dict lookup and the write in principle, and a reader relying on that not
# happening is exactly the kind of assumption this whole fix exists to not make
# again. An entry is removed only once every coroutine that was ever handed this
# exact Lock object has released it (refcount reaches zero), so a late caller can
# never start executing before an earlier one that still holds, or is still queued
# for, that same lock object — see the module docstring above for why this matters.
_locks: dict[str, asyncio.Lock] = {}
_lock_refcounts: dict[str, int] = defaultdict(int)
_locks_guard = asyncio.Lock()


async def _acquire_investigation_lock(inv_id: str) -> asyncio.Lock:
    async with _locks_guard:
        lock = _locks.setdefault(inv_id, asyncio.Lock())
        _lock_refcounts[inv_id] += 1
    await lock.acquire()
    return lock


async def _release_investigation_lock(inv_id: str, lock: asyncio.Lock) -> None:
    lock.release()
    async with _locks_guard:
        _lock_refcounts[inv_id] -= 1
        if _lock_refcounts[inv_id] <= 0:
            _locks.pop(inv_id, None)
            _lock_refcounts.pop(inv_id, None)


class Replies(BaseModel):
    ja: str
    en: str


def _confirmed_cause(inv: Investigation) -> str:
    supported = {r.hypothesis_id for r in inv.results if r.verdict == "supported"}
    for hypothesis in inv.hypotheses:
        if hypothesis.id in supported:
            return hypothesis.text
    return ""


async def apply_approval(inv: Investigation, *, approver: str, edits: dict[str, str],
                         rejected_action_ids: list[str], note: str) -> dict:
    if inv.status == "approved":
        raise ValueError(f"investigation {inv.id} is already approved")

    state = get_state()
    for section_name, new_text in edits.items():
        if inv.eight_d and hasattr(inv.eight_d, section_name):
            # Replace the section with a fresh copy rather than mutating `.text` in
            # place: EightD's eight fields may (as in the demo data and the tests)
            # share the very same EightDSection instance, so an in-place mutation
            # would silently edit every section that happened to share it, not just
            # the one named here.
            old = getattr(inv.eight_d, section_name)
            setattr(inv.eight_d, section_name, old.model_copy(update={"text": new_text}))

    # Claim the investigation before creating anything, inside a per-investigation lock
    # (task 14 review, round 2 — see the module docstring). The record-creation loop
    # below is plain code that cannot realistically fail, but the bilingual reply and
    # the quality-memory save (outside the lock, below) are both network calls that
    # can — and if either raises after the CAPA/hold/work order are already created,
    # the re-check just inside the lock must still stop a retry from creating a second
    # set of records. Persisting "approved" here, first, means a retry always finds
    # out it lost instead.
    lock = await _acquire_investigation_lock(inv.id)
    try:
        # Acquiring the lock only serialises; it does not by itself prove this caller
        # is the first to see "draft_ready". A caller that waited for the lock must
        # re-read the investigation fresh here, not trust the `inv` it was handed
        # before it ever started waiting — the winner may have already claimed and
        # fully finished while this one queued. `current is None` is NOT the same
        # thing as "already approved": it means nothing has been persisted for this
        # id yet (the unit tests below call `apply_approval` directly against a
        # freshly-built `Investigation` without first saving it — a legitimate way to
        # test this function in isolation, not a race), so there is nothing in the
        # store yet for another request to have claimed either.
        current = await asyncio.to_thread(state.get_investigation, inv.id)
        if current is not None and current.status == "approved":
            raise ValueError(f"investigation {inv.id} is already approved")

        inv.status = "approved"
        inv.approver = approver
        await asyncio.to_thread(state.save_investigation, inv)

        accepted = {a.id: a for a in inv.proposed_actions if a.id not in rejected_action_ids}
        cause = _confirmed_cause(inv)
        line = next((a.payload.get("line", "") for a in accepted.values()
                     if a.kind == "work_order"), "")
        out: dict = {"capa_id": None, "hold_id": None, "work_order_id": None,
                     "replies": None, "memory_id": None}

        for action in accepted.values():
            if action.kind == "capa":
                out["capa_id"] = await asyncio.to_thread(state.create_record, "capa", {
                    "investigation_id": inv.id, "complaint_id": inv.complaint_id,
                    "lot_id": inv.lot_id, "root_cause": cause, "owner": "Quality Manager",
                    "opened": date.today().isoformat(), "status": "open",
                    "summary": action.summary, "approver": approver, "note": note})
            elif action.kind == "hold":
                out["hold_id"] = await asyncio.to_thread(state.create_record, "hold", {
                    "investigation_id": inv.id,
                    "lots": action.payload.get("lots", inv.hold_lots),
                    "reason": cause, "raised": date.today().isoformat(), "status": "active"})
            elif action.kind == "work_order":
                out["work_order_id"] = await asyncio.to_thread(
                    state.create_record, "work_order", {
                        "investigation_id": inv.id, "line": action.payload.get("line", ""),
                        "asset": action.payload.get("asset", ""),
                        "description": action.payload.get("description", ""),
                        "raised": date.today().isoformat(), "status": "open",
                        "requested_by": approver})
    finally:
        # Released (and the dict entry cleaned up, via the refcount) as soon as the
        # claim-through-records section is done — not held across the customer-reply
        # Gemini call or the quality-memory save below. Both of those are best-effort,
        # degrade-not-explode steps (their own try/excepts, further down) that do not
        # create a second CAPA/hold/work order; by the time this lock releases,
        # `inv.status == "approved"` is already persisted, so any retry that reaches
        # this function again fails at the top-of-function check or the re-check
        # above, with or without the lock still held.
        await _release_investigation_lock(inv.id, lock)

    if any(a.kind == "customer_reply" for a in accepted.values()):
        prompt = (f"{load_prompt('customer_reply')}\n\n"
                  f"Customer complaint: {inv.complaint_id}, lot {inv.lot_id}\n"
                  f"Defect: {inv.defect.type if inv.defect else ''}\n"
                  f"Confirmed root cause: {cause}\n"
                  f"Lots contained: {', '.join(inv.hold_lots)}\n"
                  f"CAPA number: {out['capa_id']}\n"
                  f"Permanent action: {inv.eight_d.D5.text if inv.eight_d else ''}\n")
        try:
            replies = await asyncio.to_thread(generate_structured, prompt, Replies,
                                              temperature=0.3)
            out["replies"] = replies.model_dump()
        except Exception as exc:
            # Degrade, don't explode: the approval and the records already created are
            # real and must stand. Never log the prompt or the reply text — only the
            # exception's class name (PRD "no secrets, no payloads in logs").
            log.warning("customer reply generation failed: %s", exc.__class__.__name__)
            await bus.publish(inv.id, "system", "error",
                              "Could not draft the customer reply",
                              detail=exc.__class__.__name__)

    if cause:
        try:
            out["memory_id"] = await asyncio.to_thread(
                save_quality_memory, investigation_id=inv.id,
                defect_type=inv.defect.type if inv.defect else "other",
                root_cause=cause,
                parameter=next((h.parameter or "" for h in inv.hypotheses
                                if h.id in {r.hypothesis_id for r in inv.results
                                            if r.verdict == "supported"}), ""),
                line=line, capa_id=out["capa_id"] or "", lot_id=inv.lot_id)
        except Exception as exc:
            log.warning("quality memory save failed: %s", exc.__class__.__name__)
            await bus.publish(inv.id, "system", "error",
                              "Could not save the confirmed cause to quality memory",
                              detail=exc.__class__.__name__)

    await bus.publish(inv.id, "system", "done", f"8D approved by {approver}",
                      detail=note, data={k: v for k, v in out.items() if k != "replies"})
    return out
