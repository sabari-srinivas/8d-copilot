"""Seeds the five historical CAPA + quality-memory pairs behind
data.constants.PAST_INVESTIGATIONS -- completed investigations that give the
Complaints sidebar's "Past investigations" group, the CAPA tab and the Memory tab
history beyond the single CAPA-0098 story (agent/tools/capa_check.seed_historical_capa
/ agent/tools/memory.seed_historical_quality_memory). Same idempotent, fixed-id
convention as both of those: writes under the id data/generate_plant.py's
complaints.csv already carries, via state.save_record (never state.create_record), so
none of this ever consumes the live CAPA-0142.../MEM-0001... counters a real approval
advances."""
from agent.models import MemoryEntry
from agent.state import get_state
from agent.tools.llm import embed
from data.constants import PAST_INVESTIGATIONS


def _memory_text(defect_type: str, root_cause: str, parameter: str, line: str) -> str:
    """Same shape as agent.tools.memory._text, duplicated rather than imported: that
    function is private to its own module, and the five lines of duplication are
    cheaper than coupling two seeding modules through a function neither owns."""
    return f"{defect_type} on line {line}: {root_cause} (parameter {parameter})"


def seed_past_investigations() -> list[str]:
    state = get_state()
    seeded: list[str] = []
    for entry in PAST_INVESTIGATIONS:
        if state.get_record("capa", entry["capa_id"]) is not None:
            continue
        state.save_record("capa", entry["capa_id"], {
            "investigation_id": entry["investigation_id"],
            "complaint_id": entry["complaint_id"], "lot_id": entry["lot_id"],
            "root_cause": entry["root_cause"], "owner": "Quality Manager",
            "opened": entry["implemented_on"], "status": "closed",
            "summary": f"{entry['defect_type'].replace('_', ' ').title()} corrective action.",
            "approver": "Priya R.", "note": "",
        })
        mem_entry = MemoryEntry(
            id=entry["memory_id"], defect_type=entry["defect_type"],
            root_cause=entry["root_cause"], parameter=entry.get("parameter", ""),
            line=entry["line"], capa_id=entry["capa_id"], lot_id=entry["lot_id"],
            investigation_id=entry["investigation_id"],
            created=f"{entry['implemented_on']}T00:00:00+00:00")
        vector = embed([_memory_text(mem_entry.defect_type, mem_entry.root_cause,
                                     mem_entry.parameter, mem_entry.line)])[0]
        state.save_memory(mem_entry, vector)
        seeded.append(entry["capa_id"])
    return seeded
