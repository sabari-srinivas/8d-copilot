"""Investigations, records and quality memory. In-memory for tests and the local demo,
Firestore for the cloud run. Nothing outside the API writes here (PRD 13)."""
import itertools
import math
from functools import lru_cache
from typing import Protocol

from agent.config import get_settings
from agent.models import Event, Investigation, MemoryEntry

PREFIX = {"capa": "CAPA", "work_order": "WO", "hold": "H", "memory": "MEM"}
WIDTH = {"capa": 4, "work_order": 3, "hold": 2, "memory": 4}
# Demo ids follow the PRD 8 script: CAPA-0142, H-77, WO-412.
START = {"capa": 142, "work_order": 412, "hold": 77, "memory": 1}


def _new_counters() -> dict[str, itertools.count]:
    return {kind: itertools.count(start) for kind, start in START.items()}


_counters = _new_counters()


def reset_counters() -> None:
    """Test-only: the module-level counters persist across a process, which makes
    id-generating tests order-dependent unless each test resets them first."""
    global _counters
    _counters = _new_counters()


def next_id(kind: str, start: int | None = None) -> str:
    n = start if start is not None else next(_counters[kind])
    return f"{PREFIX[kind]}-{n:0{WIDTH[kind]}d}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


class StateStore(Protocol):
    def save_investigation(self, inv: Investigation) -> None: ...
    def get_investigation(self, inv_id: str) -> Investigation | None: ...
    def append_event(self, inv_id: str, event: Event) -> None: ...
    def events(self, inv_id: str) -> list[Event]: ...
    def create_record(self, kind: str, payload: dict) -> str: ...
    def get_record(self, kind: str, record_id: str) -> dict | None: ...
    def save_memory(self, entry: MemoryEntry, vector: list[float]) -> None: ...
    def search_memory(self, vector: list[float], defect_type: str,
                      k: int) -> list[tuple[MemoryEntry, float]]: ...
    def list_memory(self) -> list[MemoryEntry]: ...


class MemoryStateStore:
    def __init__(self):
        self._inv: dict[str, Investigation] = {}
        self._events: dict[str, list[Event]] = {}
        self._records: dict[str, dict[str, dict]] = {}
        self._memory: list[tuple[MemoryEntry, list[float]]] = []

    def save_investigation(self, inv): self._inv[inv.id] = inv
    def get_investigation(self, inv_id): return self._inv.get(inv_id)
    def append_event(self, inv_id, event): self._events.setdefault(inv_id, []).append(event)
    def events(self, inv_id): return list(self._events.get(inv_id, []))

    def create_record(self, kind, payload):
        record_id = next_id(kind)
        self._records.setdefault(kind, {})[record_id] = {"id": record_id, **payload}
        return record_id

    def get_record(self, kind, record_id):
        return self._records.get(kind, {}).get(record_id)

    def save_memory(self, entry, vector): self._memory.append((entry, vector))

    def search_memory(self, vector, defect_type, k):
        scored = [(e, _cosine(vector, v)) for e, v in self._memory
                  if e.defect_type == defect_type]
        return sorted(scored, key=lambda t: -t[1])[:k]

    def list_memory(self): return [e for e, _ in self._memory]


class FirestoreStateStore:
    """Collections: investigations, events, capa, holds, work_orders, memory (PRD 11)."""

    COLLECTION = {"capa": "capa", "work_order": "work_orders", "hold": "holds"}

    def __init__(self):
        from google.cloud import firestore
        s = get_settings()
        self._db = firestore.Client(project=s.gcp_project, database=s.firestore_db)

    def save_investigation(self, inv):
        self._db.collection("investigations").document(inv.id).set(inv.model_dump())

    def get_investigation(self, inv_id):
        snap = self._db.collection("investigations").document(inv_id).get()
        return Investigation.model_validate(snap.to_dict()) if snap.exists else None

    def append_event(self, inv_id, event):
        (self._db.collection("investigations").document(inv_id)
         .collection("events").document(f"{event.seq:05d}").set(event.model_dump()))

    def events(self, inv_id):
        docs = (self._db.collection("investigations").document(inv_id)
                .collection("events").order_by("seq").stream())
        return [Event.model_validate(d.to_dict()) for d in docs]

    def create_record(self, kind, payload):
        record_id = next_id(kind)
        self._db.collection(self.COLLECTION[kind]).document(record_id).set(
            {"id": record_id, **payload})
        return record_id

    def get_record(self, kind, record_id):
        snap = self._db.collection(self.COLLECTION[kind]).document(record_id).get()
        return snap.to_dict() if snap.exists else None

    def save_memory(self, entry, vector):
        from google.cloud.firestore_v1.vector import Vector
        self._db.collection("memory").document(entry.id).set(
            {**entry.model_dump(), "embedding": Vector(vector)})

    def search_memory(self, vector, defect_type, k):
        from google.cloud.firestore_v1 import FieldFilter
        from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
        from google.cloud.firestore_v1.vector import Vector
        query = (self._db.collection("memory")
                 .where(filter=FieldFilter("defect_type", "==", defect_type))
                 .find_nearest(vector_field="embedding", query_vector=Vector(vector),
                               distance_measure=DistanceMeasure.COSINE, limit=k,
                               distance_result_field="distance"))
        out = []
        for doc in query.stream():
            data = doc.to_dict()
            distance = float(data.pop("distance", 1.0))
            data.pop("embedding", None)
            # Firestore's COSINE find_nearest returns a *distance* (lower = more similar),
            # same convention as Vertex RAG. Convert to a similarity score so both
            # StateStore backends agree: higher score = more similar (see MemoryStateStore
            # above, which returns cosine similarity directly).
            out.append((MemoryEntry.model_validate(data), 1.0 - distance))
        return out

    def list_memory(self):
        out = []
        for doc in self._db.collection("memory").stream():
            data = doc.to_dict()
            data.pop("embedding", None)
            out.append(MemoryEntry.model_validate(data))
        return out


@lru_cache
def get_state() -> StateStore:
    return FirestoreStateStore() if get_settings().state_backend == "firestore" else MemoryStateStore()
