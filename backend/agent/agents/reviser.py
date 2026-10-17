"""Revises a previously submitted 8D against the customer's stated objection —
grounded editing against a critique, rather than drafting from scratch.

Shape decision (CR #14): a separate agent module, not a mode flag on writer.py.
Drafting (writer.run) and revising are genuinely different uses of the model — one
reads test results and composes a report from nothing, the other reads an existing
report plus a specific objection and edits only what the objection requires — and the
PRD's whole point is to make that difference visible, not hide it behind a branch
inside one function. A distinct `agent="reviser"` name on every event this module
publishes (see agent/models.py's AgentName and docs/contract/README.md) is what makes
it show up as its own step in the live trace, exactly like intake/vision/investigator/
evidence/writer do today.

What stays shared with writer.py, deliberately: the WriterOutput schema, the
deterministic status rule (supported hypothesis + a returned eight_d is the only way to
land on draft_ready — never the model's own status string), and the number-provenance
check (agent/tools/provenance.py). A revision is still an 8D: CLAUDE.md rule 1 (the LLM
proposes, Python decides the verdict) and rule 4 (no number outside a tool result) do
not get an exception just because the starting point was an edit instead of a blank
page. The one thing this module does NOT reuse: agent/prompts/writer.md. The prompt is
the actual behavioural difference (edit against a critique vs. compose from evidence),
so it gets its own file, agent/prompts/reviser.md.

Convention (see agent/agents/__init__.py): every blocking Gemini call runs through
asyncio.to_thread. `grounded_facts`/`allowed_numbers` are threaded for the same reason
writer.py threads them — both call plant-data functions that are network calls under
PLANT_BACKEND=bigquery.
"""
import asyncio
import json

from agent.events import bus
from agent.models import Complaint, Investigation
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.provenance import allowed_numbers, check_numbers, grounded_facts

# Mirrors writer.WriterOutput exactly (same schema, same fields) — imported from there
# rather than redefined, so the two agents can never silently drift on what shape the
# model is asked to fill in.
from agent.agents.writer import WriterOutput


def _missing_data_fallback(inv: Investigation) -> list[str]:
    """What would settle the question, stated deterministically when the model did not.
    Same logic as writer._missing_data_fallback, phrased for a revision rather than a
    first draft — kept as its own small function (not a cross-module import of a
    private helper) so this module does not reach into writer.py's internals."""
    if any(result.verdict == "supported" for result in inv.results):
        return ["A root cause was verified but no revised 8D was produced. Re-run the "
                "revision, or correct D1-D8 from the verified test result by hand."]
    inconclusive = [r.hypothesis_id for r in inv.results if r.verdict == "inconclusive"]
    tail = (f"{', '.join(inconclusive)} came back inconclusive — more lots in the "
            "comparison window, or the missing process readings for those lots, would "
            "settle them." if inconclusive else
            "Escalate to a physical inspection of the returned units and a measurement "
            "the current process data does not carry.")
    return [f"No hypothesis reached a supported verdict against the plant data, so the "
            f"rejected 8D cannot be safely revised yet. {tail}"]


async def run(inv_id: str, inv: Investigation, complaint: Complaint) -> WriterOutput:
    supported = [r for r in inv.results if r.verdict == "supported"]
    await bus.publish(inv_id, "reviser", "step_started",
                      "Revising the 8D against the customer's objection"
                      if supported else "Checking whether the evidence is enough to revise")

    facts = await asyncio.to_thread(grounded_facts, inv, complaint)
    prompt = (f"{load_prompt('reviser')}\n\n"
              f"ORIGINAL 8D (previously submitted, now rejected):\n"
              f"{json.dumps(complaint.original_eight_d, indent=2)}\n\n"
              f"CUSTOMER'S OBJECTION: {complaint.objection}\n\n"
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

    # Deterministic Python decides the status, not the model (CLAUDE.md rule 1) —
    # identical rule to writer.run, for the identical reason: a revision is still an
    # 8D, and there is still no verdict to sign without a supported hypothesis.
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
                              "Numbers in the revised draft are not backed by a tool result",
                              detail="; ".join(violations[:5]),
                              data={"message": "; ".join(violations),
                                    "violations": violations})
    await bus.publish(inv_id, "reviser", "draft_ready",
                      "Revised 8D ready for review" if out.status == "draft_ready"
                      else "Insufficient evidence to revise — escalate",
                      detail="; ".join(out.missing_data),
                      data={"status": out.status})
    return out
