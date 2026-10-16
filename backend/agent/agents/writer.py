"""Drafts the cited 8D — or says the evidence is not enough.

The writer is handed the test results plus `grounded_facts`: the per-lot reflow peaks and
the window statistics. Those are what let it ground "five of the six lots in the affected
window exceeded the limit" while reporting the complained-about lot's own peak honestly —
L2611 sits BELOW the 250 °C limit even though it is inside the drifted window, and
agent/prompts/writer.md forbids claiming otherwise.

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. `grounded_facts` and
`allowed_numbers` (`agent/tools/provenance.py`) are threaded too (task 14 follow-up):
both call `get_process_window`/`get_maintenance_events`/`get_lot_genealogy`/`joined`,
network calls under PLANT_BACKEND=bigquery — missed in the original audit because
`provenance.py` was not one of the files task 14 touched directly.
"""
import asyncio
import json

from pydantic import BaseModel

from agent.events import bus
from agent.models import Complaint, EightD, Investigation
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.provenance import allowed_numbers, check_numbers, grounded_facts


class WriterOutput(BaseModel):
    """Both the schema the model fills in and the value `run` returns.

    `status` is typed `str` rather than a Literal because it is the model that fills the
    schema, and a model that writes "Draft Ready" should not burn a retry over casing.
    The status on the value `run` hands back is never the model's: `run` overwrites it
    from the verdicts (see below), so it is always exactly one of the two words.
    """
    status: str                    # "draft_ready" or "insufficient_evidence"
    eight_d: EightD | None = None
    missing_data: list[str] = []


def _missing_data_fallback(inv: Investigation) -> list[str]:
    """What would settle the question, stated deterministically when the model did not."""
    if any(result.verdict == "supported" for result in inv.results):
        return ["A root cause was verified but no 8D draft was produced. Re-run the "
                "draft, or write D1-D8 from the verified test result by hand."]
    inconclusive = [r.hypothesis_id for r in inv.results if r.verdict == "inconclusive"]
    tail = (f"{', '.join(inconclusive)} came back inconclusive — more lots in the "
            "comparison window, or the missing process readings for those lots, would "
            "settle them." if inconclusive else
            "Escalate to a physical inspection of the returned units and a measurement "
            "the current process data does not carry.")
    return [f"No hypothesis reached a supported verdict against the plant data. {tail}"]


async def run(inv_id: str, inv: Investigation,
              complaint: Complaint | None = None) -> WriterOutput:
    supported = [r for r in inv.results if r.verdict == "supported"]
    await bus.publish(inv_id, "writer", "step_started",
                      "Drafting the 8D" if supported else "Checking whether the evidence is enough")

    facts = await asyncio.to_thread(grounded_facts, inv, complaint)
    prompt = (f"{load_prompt('writer')}\n\n"
              f"Complaint: {inv.complaint_id}, lot {inv.lot_id}\n"
              f"Defect: {inv.defect.model_dump() if inv.defect else None}\n"
              f"Hypotheses: {[h.model_dump() for h in inv.hypotheses]}\n"
              f"TEST RESULTS (the only source of numbers):"
              f" {[r.model_dump() for r in inv.results]}\n"
              f"Citations available: {[c.model_dump() for c in inv.citations]}\n"
              f"Lots to hold: {inv.hold_lots}\n"
              f"GROUNDED FACTS (tool results — the only other source of numbers):\n"
              f"{json.dumps(facts, indent=2, default=str)}\n"
              f"The complained-about lot is {inv.lot_id}. "
              f"peak_limit_breaches.lot_ids lists the lots whose own peak temperature "
              f"actually exceeded the limit — do not assert it of any other lot.\n")
    drafted = await asyncio.to_thread(generate_structured, prompt, WriterOutput,
                                      temperature=0.3)

    # Deterministic Python decides the status, not the model (CLAUDE.md rule 1). With no
    # supported hypothesis there is no verified root cause, so there is no 8D to sign; and
    # a model that fills in all eight D sections but labels them "Draft Ready", "draft" or
    # "insufficient_evidence" must not be able to mislabel a perfectly good draft. Observed
    # live: the model returned a complete, provenance-clean 8D under a status string that
    # was not "draft_ready", which stranded the investigation in insufficient_evidence.
    if supported and drafted.eight_d is not None:
        out = WriterOutput(status="draft_ready", eight_d=drafted.eight_d,
                           missing_data=drafted.missing_data)
    else:
        out = WriterOutput(status="insufficient_evidence", eight_d=None,
                           missing_data=drafted.missing_data or _missing_data_fallback(inv))

    if out.eight_d:
        allowed = await asyncio.to_thread(allowed_numbers, inv, complaint)
        violations = check_numbers(out.eight_d, allowed)
        if violations:
            await bus.publish(inv_id, "system", "error",
                              "Numbers in the draft are not backed by a tool result",
                              detail="; ".join(violations[:5]),
                              data={"message": "; ".join(violations),
                                    "violations": violations})
    await bus.publish(inv_id, "writer", "draft_ready",
                      "8D draft ready for review" if out.status == "draft_ready"
                      else "Insufficient evidence — escalate",
                      detail="; ".join(out.missing_data),
                      data={"status": out.status})
    return out
