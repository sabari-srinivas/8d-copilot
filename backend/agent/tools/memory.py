"""Quality memory: confirmed causes, found again by meaning rather than keyword (PRD 4)."""
from datetime import datetime, timezone

from agent.models import MemoryEntry
from agent.state import get_state, next_id
from agent.tools.llm import embed
from data.constants import (HISTORICAL_CAPA_DEFECT_TYPE, HISTORICAL_CAPA_ID,
                            HISTORICAL_CAPA_IMPLEMENTED_ON, HISTORICAL_CAPA_LINE,
                            HISTORICAL_CAPA_LOT, HISTORICAL_CAPA_PARAMETER,
                            HISTORICAL_CAPA_ROOT_CAUSE)

MIN_SIMILARITY = 0.6
# Paired with HISTORICAL_CAPA_ID for a human reading the two side by side, and well
# clear of the live MEM-0001, MEM-0002... counter (agent/state.py) -- this id is never
# produced by next_id("memory"), so a real approval can never collide with it.
HISTORICAL_SEED_ID = "MEM-0098"


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


def seed_historical_quality_memory() -> str | None:
    """Pre-loads the one historical confirmed cause the CAPA-effectiveness demo needs
    (CAPA-0098 -- see agent/tools/capa_check.py and data/constants.py). Quality memory
    is otherwise populated only by a live approval (agent/agents/actions.py's
    apply_approval), so without this, a freshly started server has no history for its
    first investigation to ever match against -- the "similar past case found" ->
    "did it actually work" path would never fire in a real run.

    Bypasses save_quality_memory's next_id("memory") counter on purpose: this is not a
    live approval and must never consume (or collide with) the MEM-0001, MEM-0002...
    sequence a real approval advances.

    Idempotent: a second call (e.g. a server restart against a long-lived store) is a
    no-op once HISTORICAL_SEED_ID is already present. Returns the id on the call that
    actually seeds it, None otherwise.
    """
    state = get_state()
    if any(e.id == HISTORICAL_SEED_ID for e in state.list_memory()):
        return None
    entry = MemoryEntry(
        id=HISTORICAL_SEED_ID, defect_type=HISTORICAL_CAPA_DEFECT_TYPE,
        root_cause=HISTORICAL_CAPA_ROOT_CAUSE, parameter=HISTORICAL_CAPA_PARAMETER,
        line=HISTORICAL_CAPA_LINE, capa_id=HISTORICAL_CAPA_ID, lot_id=HISTORICAL_CAPA_LOT,
        investigation_id="inv_hist_0024",
        created=f"{HISTORICAL_CAPA_IMPLEMENTED_ON}T00:00:00+00:00")
    vector = embed([_text(entry.defect_type, entry.root_cause, entry.parameter, entry.line)])[0]
    state.save_memory(entry, vector)
    return entry.id
