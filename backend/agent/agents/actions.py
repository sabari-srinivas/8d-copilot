"""What happens after a human approves. Records are created by plain code;
exactly one LLM call writes the bilingual reply (PRD 9.2).

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. `save_quality_memory` embeds under
the hood, so it goes through `asyncio.to_thread` here too, the same as
`investigator.py`'s `search_quality_memory` call. `state.save_investigation` and
`state.create_record` are threaded too (task 14 follow-up): under STATE_BACKEND=firestore
both are network calls made from this async function.
"""
import asyncio
import logging
from datetime import date

from pydantic import BaseModel

from agent.events import bus
from agent.models import Investigation
from agent.state import get_state
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.memory import save_quality_memory

log = logging.getLogger(__name__)


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

    # Claim the investigation before creating anything. The record-creation loop below
    # is plain code that cannot realistically fail, but the bilingual reply and the
    # quality-memory save are both network calls that can — and if either raises after
    # the CAPA/hold/work order are already created, the status guard above must still
    # stop a retry from creating a second set of records. Persisting "approved" here,
    # first, means a retry always hits main.py's 409 instead.
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
                "investigation_id": inv.id, "lots": action.payload.get("lots", inv.hold_lots),
                "reason": cause, "raised": date.today().isoformat(), "status": "active"})
        elif action.kind == "work_order":
            out["work_order_id"] = await asyncio.to_thread(state.create_record, "work_order", {
                "investigation_id": inv.id, "line": action.payload.get("line", ""),
                "asset": action.payload.get("asset", ""),
                "description": action.payload.get("description", ""),
                "raised": date.today().isoformat(), "status": "open",
                "requested_by": approver})

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
