"""The heart of the pipeline. The model proposes hypotheses and nothing else: every
verdict, p-value and effect size on this page comes back from `test_hypothesis`.

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. `test_hypothesis` is NOT threaded:
it is local numpy/scipy/pandas computation on an in-memory frame, no network call."""
import asyncio
import logging

from pydantic import BaseModel, Field

from agent.events import bus
from agent.models import Defect, Hypothesis, HypothesisResult, MemoryEntry
from agent.tools.llm import generate_structured, load_prompt
from agent.tools.memory import search_quality_memory
from agent.tools.plant_data import get_lot_genealogy, get_maintenance_events, get_process_window
from agent.tools.stats_test import test_hypothesis

log = logging.getLogger(__name__)


class HypothesisList(BaseModel):
    hypotheses: list[Hypothesis] = Field(min_length=3, max_length=5)


def _unverified(events: list[dict]) -> list[dict]:
    """Maintenance events whose follow-up check was never closed out — the escape point
    a drifted process hides behind. Read from the record, never matched on a work-order id."""
    return [event for event in events
            if "pending" in str(event.get("post_check", "")).lower()]


def _renumber(proposed: list[Hypothesis]) -> list[Hypothesis]:
    """Force the ids to H1..Hn in the order proposed.

    agent/prompts/investigator.md instructs the model to do this, and the live model has
    been observed inventing ids like `solder_bridge_h1` anyway. The UI's hypothesis cards
    and the 8D's cross-references key off these ids, so a prompt violation must not be
    able to corrupt them: a prompt instruction is not a guarantee.
    """
    renumbered = []
    for index, hypothesis in enumerate(proposed, start=1):
        wanted = f"H{index}"
        if hypothesis.id != wanted:
            log.info("renumbered proposed hypothesis %r to %s", hypothesis.id, wanted)
        renumbered.append(hypothesis.model_copy(update={"id": wanted}))
    return renumbered


async def run(inv_id: str, lot_id: str, defect: Defect,
              traveler_note: str = "") -> tuple[list[Hypothesis], list[HypothesisResult],
                                                list[MemoryEntry]]:
    await bus.publish(inv_id, "investigator", "step_started", "Checking quality memory")
    hits = await asyncio.to_thread(search_quality_memory, defect.type,
                                   f"{defect.type} {defect.visual_evidence}")
    for hit in hits:
        await bus.publish(inv_id, "investigator", "memory_hit",
                          f"Similar past case found: {hit.capa_id}",
                          detail=hit.root_cause, data=hit.model_dump())
    if not hits:
        await bus.publish(inv_id, "investigator", "tool_result", "No similar past case found",
                          data={"tool": "search_quality_memory",
                                "summary": "No similar past case found"})

    genealogy = get_lot_genealogy(lot_id)
    window = get_process_window()
    events = get_maintenance_events(genealogy["line"])
    await bus.publish(inv_id, "investigator", "tool_call",
                      f"Pulling lot genealogy and process window for {lot_id}",
                      detail=f"Line {genealogy['line']}, shift {genealogy['shift']}, "
                             f"{window['n_lots']} lots in the last {window['days']} days",
                      data={"tool": "get_lot_genealogy", "args": {"lot_id": lot_id}})
    for record in _unverified(events):
        # The pivotal fact of the whole investigation, surfaced as its own card
        # (docs/contract/mock_events.json seq 8). Found by reading post_check, not by
        # naming a work order: any pending profile check on this line gets the same card.
        found = f"Found maintenance event {record['wo_id']} on Line {record['line'][-1]}"
        await bus.publish(inv_id, "investigator", "tool_result", found,
                          detail=f"{record['date']} · {record['asset']} · "
                                 f"{record['description']} · post-check "
                                 f"{record['post_check'].replace('_', ' ')}",
                          data={"tool": "get_maintenance_events", "summary": found, **record})

    prompt = (f"{load_prompt('investigator')}\n\n"
              f"Defect: {defect.type} ({defect.severity}). {defect.visual_evidence}\n"
              f"Affected lot: {genealogy}\n"
              f"Process window: {window}\n"
              f"Maintenance events on this line: {events}\n"
              f"Quality memory hits: {[h.model_dump() for h in hits]}\n"
              f"Shift-lead notes: {traveler_note or 'none'}\n")
    generated = await asyncio.to_thread(generate_structured, prompt, HypothesisList)
    proposed = _renumber(generated.hypotheses)

    results: list[HypothesisResult] = []
    for hypothesis in proposed:
        await bus.publish(inv_id, "investigator", "hypothesis",
                          f"{hypothesis.id} {hypothesis.text}",
                          detail=f"{hypothesis.category} · "
                                 f"{hypothesis.parameter or hypothesis.event_wo_id} · "
                                 f"expected {hypothesis.direction}",
                          data=hypothesis.model_dump())
        await bus.publish(inv_id, "investigator", "tool_call",
                          f"Testing: {hypothesis.text}",
                          detail="Comparing defect lots with good lots of the same product",
                          data={"tool": "test_hypothesis",
                                "args": {"hypothesis_id": hypothesis.id, "lot_id": lot_id,
                                         "parameter": hypothesis.parameter,
                                         "event_wo_id": hypothesis.event_wo_id,
                                         "direction": hypothesis.direction}})
        try:
            result = test_hypothesis(hypothesis.id, lot_id, parameter=hypothesis.parameter,
                                     event_wo_id=hypothesis.event_wo_id,
                                     direction=hypothesis.direction)
        except ValueError as exc:
            await bus.publish(inv_id, "investigator", "tool_result",
                              f"{hypothesis.id} could not be tested", detail=str(exc),
                              data={"tool": "test_hypothesis", "summary": str(exc),
                                    "hypothesis_id": hypothesis.id})
            continue
        results.append(result)
        await bus.publish(inv_id, "investigator", "hypothesis_result",
                          f"{hypothesis.id} {result.verdict}",
                          detail=f"{result.test}, p = {result.p_value:.4f}, {result.effect}",
                          data=result.model_dump())
    return proposed, results, hits
