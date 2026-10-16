"""Finds the quality documents that back the surviving hypotheses.

Retrieval is asked for the top `k=3` per query and the results are kept as a SET, not
ranked down to a single winner. The measured margins in this corpus are thin — PFMEA
Row 14 wins its query by 0.069 and Control plan Item 6 by 0.050, because several PFMEA
rows share near-identical maintenance wording — so no logic here may depend on a
particular document coming first. The evidence screen shows several citation cards.
"""
from agent.events import bus
from agent.models import Citation, Investigation, Passage
from agent.tools.doc_search import search_quality_docs
from data.constants import PARAM_LABELS

K = 3
CHART_LABEL = "Chart: reflow peak temp by lot"
# How a filename is spoken in a citation bracket. Anything not listed falls back to the
# stem with underscores turned to spaces.
SOURCE_LABELS = {"pfmea.md": "PFMEA", "control_plan.md": "Control plan",
                 "past_8d_tombstoning.md": "Past 8D (tombstoning)",
                 "past_8d_voids.md": "Past 8D (voids)"}
# Refs that read naturally lowercased inside a label: "PFMEA row 14", not "PFMEA Row 14".
LOWERCASED_REFS = ("Row", "Item")


def _label(passage: Passage) -> str:
    source = SOURCE_LABELS.get(passage.source,
                               passage.source.removesuffix(".md").replace("_", " ").capitalize())
    ref = passage.ref
    if ref.split(" ")[0] in LOWERCASED_REFS:
        ref = ref[0].lower() + ref[1:]
    return f"{source} {ref}"


def _queries(inv: Investigation) -> list[str]:
    """One query per hypothesis still standing, built from the defect and the parameter
    it named. A hypothesis anchored on a maintenance event gets a second query about the
    control that should have caught it — that is the other half of 'why it escaped'."""
    verdicts = {result.hypothesis_id: result.verdict for result in inv.results}
    wanted = {"supported"} if "supported" in verdicts.values() else {"inconclusive"}
    standing = [h for h in inv.hypotheses if verdicts.get(h.id) in wanted]
    defect = (inv.defect.type if inv.defect else "defect").replace("_", " ")

    queries: list[str] = []
    for hypothesis in standing:
        parameter = PARAM_LABELS.get(hypothesis.parameter or "",
                                     (hypothesis.parameter or "").replace("_", " "))
        queries.append(f"{defect} caused by {parameter}: {hypothesis.text}".strip())
        if hypothesis.event_wo_id:
            queries.append("what must be done to verify the reflow profile after "
                           "oven maintenance, and which control detects it")
    if not queries:
        queries.append(f"{defect} cause, detection control and prevention")
    return queries


async def run(inv_id: str, inv: Investigation) -> list[Citation]:
    await bus.publish(inv_id, "evidence", "step_started",
                      "Looking for the PFMEA row and control plan item that cover this")

    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for query in _queries(inv):
        await bus.publish(inv_id, "evidence", "tool_call",
                          "Searching the quality documents", detail=query,
                          data={"tool": "search_quality_docs",
                                "args": {"query": query, "k": K}})
        for passage in search_quality_docs(query, k=K):
            key = (passage.source, passage.ref)
            if key in seen:
                continue
            seen.add(key)
            citation = Citation(label=_label(passage), source=passage.source,
                                ref=passage.ref, quote=passage.quote)
            citations.append(citation)
            await bus.publish(inv_id, "evidence", "citation", citation.label,
                              detail=citation.quote, data=citation.model_dump())

    if inv.chart_url:
        chart = Citation(label=CHART_LABEL, source="chart", ref=inv.chart_url,
                         quote="Reflow peak temperature by lot, drawn from the lot "
                               "records — synthetic demo data.")
        citations.append(chart)
        await bus.publish(inv_id, "evidence", "citation", chart.label,
                          detail=chart.quote, data=chart.model_dump())

    gathered = f"{len(citations)} citations gathered"
    await bus.publish(inv_id, "evidence", "tool_result", gathered,
                      detail=" · ".join(c.label for c in citations),
                      data={"tool": "search_quality_docs", "summary": gathered,
                            "labels": [c.label for c in citations]})
    return citations
