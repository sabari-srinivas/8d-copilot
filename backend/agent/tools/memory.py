"""Quality memory: confirmed causes, found again by meaning rather than keyword (PRD 4)."""
from datetime import datetime, timezone

from agent.models import MemoryEntry
from agent.state import get_state, next_id
from agent.tools.llm import embed

MIN_SIMILARITY = 0.6


def _text(defect_type: str, root_cause: str, parameter: str, line: str) -> str:
    return f"{defect_type} on line {line}: {root_cause} (parameter {parameter})"


def save_quality_memory(*, investigation_id: str, defect_type: str, root_cause: str,
                        parameter: str = "", line: str = "", capa_id: str = "",
                        lot_id: str = "") -> str:
    entry = MemoryEntry(
        id=next_id("memory"), defect_type=defect_type, root_cause=root_cause,
        parameter=parameter, line=line, capa_id=capa_id, lot_id=lot_id,
        investigation_id=investigation_id,
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    vector = embed([_text(defect_type, root_cause, parameter, line)])[0]
    get_state().save_memory(entry, vector)
    return entry.id


def search_quality_memory(defect_type: str, query: str, k: int = 2) -> list[MemoryEntry]:
    vector = embed([query])[0]
    hits = get_state().search_memory(vector, defect_type=defect_type, k=k)
    return [entry for entry, score in hits if score >= MIN_SIMILARITY]


def list_quality_memory() -> list[MemoryEntry]:
    return get_state().list_memory()
