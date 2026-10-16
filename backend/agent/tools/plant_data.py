"""Plant data behind one protocol. CSV for tests and the local demo, BigQuery for the
cloud run. Switch with PLANT_BACKEND. No LLM touches this file."""
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import pandas as pd

from agent.config import get_settings
from data.constants import (DEFECT_RATE_THRESHOLD, PARAM_UNITS, PRODUCT,
                            REFLOW_PEAK_LIMIT_C)

OUT = Path(__file__).resolve().parents[2] / "data" / "out"
NUMERIC_PARAMS = [p for p in PARAM_UNITS if p != "operator_id"]


class PlantStore(Protocol):
    def lots(self) -> pd.DataFrame: ...
    def process(self) -> pd.DataFrame: ...
    def maintenance(self) -> pd.DataFrame: ...
    def complaints(self) -> pd.DataFrame: ...


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


class BigQueryPlantStore:
    """Reads the BigQuery dataset loaded by infra/load_data.sh."""

    def __init__(self):
        from google.cloud import bigquery
        s = get_settings()
        self._client = bigquery.Client(project=s.gcp_project)
        self._dataset = f"{s.gcp_project}.{s.bq_dataset}"

    def _read(self, name: str) -> pd.DataFrame:
        return self._client.query(f"SELECT * FROM `{self._dataset}.{name}`").to_dataframe()

    def lots(self): return self._read("lots")
    def process(self): return self._read("process")
    def maintenance(self): return self._read("maintenance")
    def complaints(self): return self._read("complaints")


@lru_cache
def get_store() -> PlantStore:
    return BigQueryPlantStore() if get_settings().plant_backend == "bigquery" else CsvPlantStore()


@lru_cache
def joined() -> pd.DataFrame:
    store = get_store()
    df = store.lots().merge(store.process(), on="lot_id")
    df["date"] = pd.to_datetime(df["date"])
    df["bridge_rate"] = df.defects_solder_bridge / df.qty
    # Defensive copy: this DataFrame is lru_cache'd and shared by every caller across the
    # process. Without the copy, the first caller that mutates its result (even via a
    # column assignment on what looks like a local variable) would silently poison the
    # one cached object for everyone else. The copy is cheap next to the CSV read above.
    return df.copy()


def _reset_caches() -> None:
    """Clear get_store/joined caches. For tests only — production code never calls this.

    get_store() and joined() are @lru_cache'd on purpose for request-path performance,
    but that means a test that regenerates the CSVs or flips PLANT_BACKEND mid-session
    would silently keep reading stale data without this.
    """
    get_store.cache_clear()
    joined.cache_clear()


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
    m = get_store().maintenance()
    m = m[m.line == line]
    if since:
        m = m[pd.to_datetime(m.date) >= pd.Timestamp(since)]
    return m.sort_values("date").to_dict("records")


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
