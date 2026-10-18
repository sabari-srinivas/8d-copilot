"""Plant data behind one protocol. CSV for tests and the local demo, BigQuery for the
cloud run. Switch with PLANT_BACKEND. No LLM touches this file."""
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import pandas as pd

from agent.config import get_settings
from agent.models import MaintenanceEvent, PlantLot
from data.constants import (CATEGORICAL_PARAMS, DEFECT_RATE_THRESHOLD, PARAM_UNITS,
                            PRODUCT, REFLOW_PEAK_LIMIT_C)

OUT = Path(__file__).resolve().parents[2] / "data" / "out"
NUMERIC_PARAMS = [p for p in PARAM_UNITS if p not in CATEGORICAL_PARAMS]


class PlantStore(Protocol):
    def lots(self) -> pd.DataFrame: ...
    def process(self) -> pd.DataFrame: ...
    def maintenance(self) -> pd.DataFrame: ...
    def complaints(self) -> pd.DataFrame: ...
    def capa_lots(self) -> pd.DataFrame: ...


class CsvPlantStore:
    """Reads data/out/*.csv produced by data/generate_plant.py."""

    def _read(self, name: str) -> pd.DataFrame:
        path = OUT / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. Run `python -m data.generate_plant` first.")
        return pd.read_csv(path)

    def lots(self): return self._read("lots")
    def process(self): return self._read("process")
    def maintenance(self): return self._read("maintenance")
    def complaints(self): return self._read("complaints")
    def capa_lots(self): return self._read("capa_lots")


def _stringify_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise BigQuery's DATE columns to plain ISO strings, in place.

    `bigquery.QueryJob.to_dataframe()` returns a DATE column as dtype `dbdate`
    (`datetime.date` objects), unlike `pd.read_csv`, which leaves every column as plain
    text. Lots/process dates already get converted through `pd.to_datetime` +
    `strftime` in `_joined_cached`/`get_lot_genealogy`, so those are safe either way —
    but `get_maintenance_events` hands its rows straight through
    (`m.sort_values("date").to_dict("records")`), and that record is later spread
    verbatim into an `Event.data` dict (`agent/agents/investigator.py`). A raw
    `datetime.date` there is not JSON-serialisable (breaks the SSE stream's
    `json.dumps`) and not Firestore-serialisable (`FirestoreStateStore.append_event`
    raises `TypeError: Cannot convert to a Firestore Value` on one) — found by running
    PLANT_BACKEND=bigquery together with STATE_BACKEND=firestore (task 14). Converting
    once, here, at the one place both backends' date columns funnel through, keeps
    every caller's assumption (a plain string, exactly what CSV already handed them)
    true regardless of which PlantStore is behind `get_store()`.
    """
    for col in df.columns:
        if str(df[col].dtype) in ("dbdate", "dbtime") or "datetime64" in str(df[col].dtype):
            df[col] = df[col].astype(str)
    return df


class BigQueryPlantStore:
    """Reads the BigQuery dataset loaded by infra/load_data.sh."""

    def __init__(self):
        from google.cloud import bigquery
        s = get_settings()
        self._client = bigquery.Client(project=s.gcp_project)
        self._dataset = f"{s.gcp_project}.{s.bq_dataset}"

    def _read(self, name: str) -> pd.DataFrame:
        df = self._client.query(f"SELECT * FROM `{self._dataset}.{name}`").to_dataframe()
        return _stringify_dates(df)

    def lots(self): return self._read("lots")
    def process(self): return self._read("process")
    def maintenance(self): return self._read("maintenance")
    def complaints(self): return self._read("complaints")
    def capa_lots(self): return self._read("capa_lots")


@lru_cache
def get_store() -> PlantStore:
    return BigQueryPlantStore() if get_settings().plant_backend == "bigquery" else CsvPlantStore()


@lru_cache(maxsize=None)
def _table_cached(name: str) -> pd.DataFrame:
    """One read per table per process, for the three tables `_joined_cached` doesn't
    already cover.

    Under PLANT_BACKEND=bigquery every `PlantStore._read` is a network round trip, and
    the uncached reads were being made per *item* rather than per request:
    `get_capa_lots` is called once per CAPA by `list_capas_with_effectiveness`, so
    `GET /api/capas` with 8 CAPAs issued 8 identical `SELECT * FROM capa_lots` queries
    and took ~7.5 s. `GET /api/dashboard/summary` does the same work plus a complaints
    read and took ~8.7 s. Measured, not guessed — see docs/CHANGE_REQUESTS.md #18.

    These are static reference tables: they change when `infra/load_data.sh` runs
    `bq load`, which is a deploy-time action, never a request-time one. Caching them for
    the life of the process is the same decision `_joined_cached` already makes about
    lots+process, extended to the rest.

    Never returned directly — every caller goes through a wrapper that copies, so one
    caller's in-place mutation cannot poison the next (the bug that split
    `joined()`/`_joined_cached()` in the first place).
    """
    return getattr(get_store(), name)()


def _table(name: str) -> pd.DataFrame:
    """A private copy of a cached reference table. See `_table_cached`."""
    return _table_cached(name).copy()


@lru_cache
def _joined_cached() -> pd.DataFrame:
    """Reads and joins the CSVs once per process. Never returned directly — joined()
    is the public entry point and always hands back a copy of this frame."""
    store = get_store()
    df = store.lots().merge(store.process(), on="lot_id")
    df["date"] = pd.to_datetime(df["date"])
    df["bridge_rate"] = df.defects_solder_bridge / df.qty
    return df


def joined() -> pd.DataFrame:
    """Lots joined to process with a bridge_rate column.

    Returns a fresh copy on every call: the underlying frame is cached for the life of
    the process (via _joined_cached, @lru_cache), so handing out the cached object
    itself would let one caller's in-place mutation poison every later caller. The
    copy happens here, outside the cached function, so it runs on every call rather
    than once on the first cache miss.
    """
    return _joined_cached().copy()


def warm_plant_cache() -> None:
    """Fill every plant-data cache up front, so no request pays for the first read.

    Called once from the app's lifespan (agent/main.py). Under PLANT_BACKEND=bigquery
    this is five network reads; under csv it is five small file reads and effectively
    free. Safe to call more than once — each underlying read is @lru_cache'd, so a
    second call is a no-op.
    """
    _joined_cached()
    for name in ("complaints", "maintenance", "capa_lots"):
        _table_cached(name)


def _reset_caches() -> None:
    """Clear every plant-data cache. For tests only — production code never calls this.

    These are @lru_cache'd on purpose for request-path performance, but that means a
    test that regenerates the CSVs or flips PLANT_BACKEND mid-session would silently
    keep reading stale data without this. Any new cache in this module must be added
    here too, or it becomes a source of cross-test contamination that only shows up as
    an unrelated test failing in a particular order.
    """
    get_store.cache_clear()
    _joined_cached.cache_clear()
    _table_cached.cache_clear()


def get_lot_genealogy(lot_id: str) -> dict:
    df = joined()
    hit = df[df.lot_id == lot_id]
    if hit.empty:
        raise KeyError(f"unknown lot {lot_id}")
    row = hit.iloc[0]
    return {
        "lot_id": row.lot_id, "line": row.line, "shift": row["shift"],
        "date": row.date.strftime("%Y-%m-%d"), "product": row["product"], "qty": int(row.qty),
        "paste_lot": row.paste_lot, "stencil_id": row.stencil_id, "operator_id": row.operator_id,
        "defects_solder_bridge": int(row.defects_solder_bridge),
        "defects_other": int(row.defects_other),
        "bridge_rate": round(float(row.bridge_rate), 4), "ship_status": row.ship_status,
    }


def get_process_window(product: str = PRODUCT, days: int = 30) -> dict:
    # An unknown `product` filters to an empty frame; `df.date.max()` on that is NaT,
    # every comparison against NaT is False, and this returns an empty-but-valid result
    # rather than raising. Not a brief requirement (only unknown lot / missing CSV must
    # raise), but worth knowing if a caller ever passes an unvalidated product string.
    df = joined()
    df = df[df["product"] == product]
    cutoff = df.date.max() - pd.Timedelta(days=days)
    df = df[df.date >= cutoff]
    return {
        "product": product,
        "days": days,
        "n_lots": int(len(df)),
        "parameters": {
            p: {"unit": PARAM_UNITS[p], "mean": round(float(df[p].mean()), 2),
                "min": round(float(df[p].min()), 2), "max": round(float(df[p].max()), 2)}
            for p in NUMERIC_PARAMS
        },
        "categorical": {"operator_id": sorted(df.operator_id.unique().tolist()),
                        "stencil_id": sorted(df.stencil_id.unique().tolist()),
                        "line": sorted(df.line.unique().tolist())},
        "limits": {"reflow_peak_temp_c": REFLOW_PEAK_LIMIT_C},
    }


def get_maintenance_events(line: str, since: str | None = None) -> list[dict]:
    m = _table("maintenance")
    m = m[m.line == line]
    if since:
        m = m[pd.to_datetime(m.date) >= pd.Timestamp(since)]
    return m.sort_values("date").to_dict("records")


def get_capa_lots(capa_id: str) -> pd.DataFrame:
    """Historical, per-lot evidence for one CAPA, from the seed table written by
    data/generate_plant.py (data/out/capa_lots.csv). Columns: capa_id, lot_id, line,
    date, product, defect_type, qty, defects, complaint_id.

    Returns an empty frame for any capa_id with no seed row -- in particular, every
    CAPA created at runtime by a live approval (agent/agents/actions.py), which exists
    only in agent.state, never in this CSV. See get_capa_defect_series for the fallback
    that covers that case.
    """
    rows = _table_cached("capa_lots")
    return rows[rows.capa_id == capa_id].copy()


def get_capa_defect_series(capa_id: str, line: str, defect_type: str) -> pd.DataFrame:
    """Per-lot defect rate to evaluate one CAPA's effect on `defect_type`, oldest lot
    first. Columns: lot_id, date (Timestamp), rate. Two sources, tried in this order:

    1. The seed table (get_capa_lots) -- CAPAs planted purely for the
       effectiveness-verification demo (agent/tools/capa_check.py), weeks before the
       current lots/process window and never merged into joined(), so they cannot move
       a single p-value data/check_plant.py checks.
    2. joined(), scoped to `line`, for a capa_id with no seed row -- i.e. every CAPA
       created at runtime by a live approval. The per-lot rate is `bridge_rate` for
       defect_type "solder_bridge" (the only defect this dataset tracks with its own
       counter) and `defects_other / qty` for everything else, the one bucket every
       other defect type falls into in this schema.
    """
    hist = get_capa_lots(capa_id)
    if not hist.empty:
        if "line" in hist.columns:
            hist = hist[hist.line == line]
        hist = hist.copy()
        hist["date"] = pd.to_datetime(hist["date"])
        hist["rate"] = hist.defects / hist.qty
        return hist[["lot_id", "date", "rate"]].sort_values("date").reset_index(drop=True)

    df = joined()
    df = df[df.line == line].copy()
    df["rate"] = df["bridge_rate"] if defect_type == "solder_bridge" else df.defects_other / df.qty
    return df[["lot_id", "date", "rate"]].sort_values("date").reset_index(drop=True)


def list_plant_lots() -> list[PlantLot]:
    """GET /api/plant/lots -- the Plant tab's receipts: all 64 lots joined to their 9
    measured process parameters. Deliberately returns every lot, not a 30-day window
    (unlike get_process_window) -- this is the "click through and see the data is
    real" screen, not a statistics input."""
    df = joined().sort_values("date")
    return [
        PlantLot(
            lot_id=r.lot_id, line=r.line, shift=r.shift,
            date=r.date.strftime("%Y-%m-%d"), product=r.product, qty=int(r.qty),
            paste_lot=r.paste_lot, stencil_id=r.stencil_id, operator_id=r.operator_id,
            defects_solder_bridge=int(r.defects_solder_bridge),
            defects_other=int(r.defects_other), bridge_rate=round(float(r.bridge_rate), 4),
            ship_status=r.ship_status, reflow_peak_temp_c=float(r.reflow_peak_temp_c),
            time_above_liquidus_s=float(r.time_above_liquidus_s),
            preheat_ramp_c_per_s=float(r.preheat_ramp_c_per_s),
            soak_time_s=float(r.soak_time_s),
            conveyor_speed_cm_min=float(r.conveyor_speed_cm_min),
            paste_age_h=float(r.paste_age_h), room_humidity_pct=float(r.room_humidity_pct),
            stencil_print_count=float(r.stencil_print_count),
            squeegee_pressure_kg=float(r.squeegee_pressure_kg),
        )
        for r in df.itertuples()
    ]


def list_maintenance() -> list[MaintenanceEvent]:
    """GET /api/plant/maintenance -- all 10 work orders across both lines (unlike
    get_maintenance_events, which filters to one line for the investigator).

    `pd.read_csv`'s default `na_values` treats the literal text "n/a" already written
    into maintenance.csv (data/generate_plant.py's post_check column) as a MISSING
    value, not the string "n/a" -- so CsvPlantStore().maintenance() hands this back as
    float NaN, which MaintenanceEvent (a plain `str` field) rejects. `fillna` restores
    the original literal text; BigQueryPlantStore never has this problem (a DB column
    has no such "n/a" sentinel), so this is CSV-backend-only, same as
    plant_data._stringify_dates's DATE-column fixup above.
    """
    m = _table("maintenance").fillna("n/a").sort_values("date")
    return [MaintenanceEvent(**row) for row in m.to_dict("records")]


def get_comparison_groups(lot_id: str, product: str = PRODUCT, days: int = 30) -> dict:
    """Defect lots vs good lots of the same product in the last `days` (PRD 9.3).

    Same empty-but-valid caveat as get_process_window: an unknown `product` yields
    empty defect_lots/good_lots rather than an error.
    """
    df = joined()
    df = df[df["product"] == product]
    cutoff = df.date.max() - pd.Timedelta(days=days)
    df = df[df.date >= cutoff]
    defect = df[df.bridge_rate > DEFECT_RATE_THRESHOLD]
    good = df[df.bridge_rate <= DEFECT_RATE_THRESHOLD]
    return {
        "lot_id": lot_id,
        "defect_lots": sorted(defect.lot_id.tolist()),
        "good_lots": sorted(good.lot_id.tolist()),
        "defect_rate_threshold": DEFECT_RATE_THRESHOLD,
        "window_days": days,
    }
