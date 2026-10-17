import datetime
import json

import db_dtypes  # noqa: F401  -- registers the "dbdate" extension dtype with pandas
import pandas as pd
import pytest
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT, PRODUCT
from agent.tools import plant_data as pd_tools


@pytest.fixture(scope="module")
def store():
    return pd_tools.CsvPlantStore()


def test_lots_cover_the_whole_window(store):
    lots = store.lots()
    assert len(lots) == 64
    assert set(lots["product"]) == {PRODUCT}


def test_lot_genealogy_returns_the_fields_the_8d_needs():
    g = pd_tools.get_lot_genealogy(GOLDEN_LOT)
    assert g["lot_id"] == GOLDEN_LOT
    assert g["line"] == "L2"
    assert g["defects_solder_bridge"] == 14
    assert {"shift", "operator_id", "stencil_id", "paste_lot", "qty", "date"} <= set(g)
    # Value correctness, not just key presence: a column name that collides with a
    # pandas Series/DataFrame method (e.g. "shift" vs Series.shift()) would leave this
    # key present but bound to a method object instead of the real value. A real shift
    # is one of the three generated letters, and json.dumps round-trips every scalar
    # field here — a bound method fails to serialize and would fail this assertion.
    assert g["shift"] in {"A", "B", "C"}
    assert isinstance(g["operator_id"], str) and g["operator_id"].startswith("OP-")
    assert json.dumps(g)  # raises TypeError if any field is a non-serializable object


def test_comparison_groups_split_defect_from_good():
    groups = pd_tools.get_comparison_groups(GOLDEN_LOT)
    assert sorted(groups["defect_lots"]) == sorted(DRIFT_LOT_IDS)
    assert GOLDEN_LOT in groups["defect_lots"]
    assert not set(groups["defect_lots"]) & set(groups["good_lots"])
    assert len(groups["good_lots"]) > 40


def test_maintenance_events_find_the_escape_point():
    events = pd_tools.get_maintenance_events("L2")
    wo388 = next(e for e in events if e["wo_id"] == "WO-388")
    assert wo388["post_check"] == "profile_verification_pending"
    assert "zone 7" in wo388["description"].lower()


def test_process_window_lists_testable_parameters():
    w = pd_tools.get_process_window()
    assert "reflow_peak_temp_c" in w["parameters"]
    assert w["parameters"]["reflow_peak_temp_c"]["unit"] == "°C"
    assert w["limits"]["reflow_peak_temp_c"] == 250.0


def test_joined_adds_bridge_rate():
    df = pd_tools.joined()
    assert "bridge_rate" in df.columns
    assert df.loc[df.lot_id == GOLDEN_LOT, "bridge_rate"].iloc[0] > 0.012


def test_joined_returns_a_fresh_copy_so_callers_cannot_poison_the_cache():
    df1 = pd_tools.joined()
    df2 = pd_tools.joined()
    assert df1 is not df2  # different objects on every call ...

    df1["bridge_rate"] = 999.0  # ... so mutating one caller's frame ...
    assert pd_tools.joined()["bridge_rate"].iloc[0] != 999.0  # ... never reaches another.

    # The CSV read + join itself is still cached underneath (request-path performance):
    # repeated joined() calls must not keep re-reading disk.
    hits_before = pd_tools._joined_cached.cache_info().hits
    pd_tools.joined()
    assert pd_tools._joined_cached.cache_info().hits > hits_before


def test_unknown_lot_raises_a_clear_error():
    with pytest.raises(KeyError, match="L9999"):
        pd_tools.get_lot_genealogy("L9999")


def test_stringify_dates_turns_bigquery_date_columns_into_plain_strings():
    """task 14: BigQuery's to_dataframe() returns a DATE column as dtype `dbdate`
    (datetime.date objects), not a plain string like pd.read_csv — found when
    get_maintenance_events's raw record, with a dbdate `date` field, was spread into an
    Event.data dict and broke both json.dumps (the SSE stream) and
    FirestoreStateStore.append_event (STATE_BACKEND=firestore) with 'Cannot convert to
    a Firestore Value'. No network call: builds the same dtype BigQuery would return,
    using the same db-dtypes package bigquery.to_dataframe() depends on."""
    df = pd.DataFrame({
        "wo_id": ["WO-1", "WO-2"],
        "date": pd.Series([datetime.date(2026, 10, 8), datetime.date(2026, 9, 19)],
                          dtype="dbdate"),
    })
    out = pd_tools._stringify_dates(df)
    assert out["date"].tolist() == ["2026-10-08", "2026-09-19"]
    assert all(isinstance(v, str) for v in out["date"])
    assert json.dumps(out.to_dict("records"))  # raises TypeError if still a date object

    # Columns that are already plain strings (the CSV-backend shape) pass through
    # unchanged — this function must be safe to apply unconditionally.
    untouched = pd.DataFrame({"wo_id": ["WO-1"], "date": ["2026-10-08"]})
    assert pd_tools._stringify_dates(untouched)["date"].tolist() == ["2026-10-08"]


def test_capa_lots_returns_only_the_requested_capa():
    from data.constants import HISTORICAL_CAPA_ID
    rows = pd_tools.get_capa_lots(HISTORICAL_CAPA_ID)
    assert len(rows) == 24
    assert set(rows.capa_id) == {HISTORICAL_CAPA_ID}
    assert rows.empty is False

    missing = pd_tools.get_capa_lots("CAPA-NOPE")
    assert missing.empty


def test_capa_defect_series_reads_the_historical_seed_table():
    from data.constants import (HISTORICAL_CAPA_DEFECT_TYPE, HISTORICAL_CAPA_ID,
                                HISTORICAL_CAPA_LINE)
    series = pd_tools.get_capa_defect_series(HISTORICAL_CAPA_ID, HISTORICAL_CAPA_LINE,
                                             HISTORICAL_CAPA_DEFECT_TYPE)
    assert list(series.columns) == ["lot_id", "date", "rate"]
    assert len(series) == 24
    assert series["date"].is_monotonic_increasing
    assert (series["rate"] >= 0).all()


def test_capa_defect_series_falls_back_to_joined_for_a_live_capa():
    """A CAPA created at runtime (agent/agents/actions.py) has no seed row -- the
    series must come from the real lots/process join instead, scoped to the line."""
    series = pd_tools.get_capa_defect_series("CAPA-0142", "L2", "solder_bridge")
    assert not series.empty
    assert set(series.lot_id) <= set(pd_tools.joined().query("line == 'L2'").lot_id)
    joined_bridge = pd_tools.joined().set_index("lot_id")["bridge_rate"]
    for row in series.itertuples():
        assert row.rate == pytest.approx(joined_bridge[row.lot_id])


def test_bigquery_store_capa_lots_goes_through_stringify_dates(monkeypatch):
    """BigQueryPlantStore.capa_lots() must funnel through the same _stringify_dates
    boundary as every other table (lots/process/maintenance/complaints). capa_lots.csv
    has its own `date` column (data/generate_plant.py), and `bq load --autodetect`
    infers it as BigQuery DATE just like the others -- confirmed live against
    d-copilot-2026.plant.capa_lots (`bq show --schema` reports `date: DATE`). Without
    this, get_capa_defect_series/verify_capa_effectiveness would hand a raw
    datetime.date through to callers under PLANT_BACKEND=bigquery while the CSV
    backend hands a plain string -- the exact task-14 trap (broke json.dumps for the
    SSE stream and Firestore's append_event) hitting a different table.

    Hermetic: `google.cloud.bigquery.Client` is replaced with a fake that returns a
    `dbdate`-typed frame, mirroring what the real client's `to_dataframe()` yields, so
    nothing here talks to the network or needs PLANT_BACKEND=bigquery at import time.
    """
    import datetime
    from types import SimpleNamespace

    fake_df = pd.DataFrame({
        "capa_id": ["CAPA-0098"], "lot_id": ["L2380"],
        "date": pd.Series([datetime.date(2026, 6, 1)], dtype="dbdate"),
    })

    class FakeQueryJob:
        def to_dataframe(self):
            return fake_df

    class FakeClient:
        def __init__(self, project=None):
            self.project = project

        def query(self, sql):
            assert "capa_lots" in sql
            return FakeQueryJob()

    monkeypatch.setattr("google.cloud.bigquery.Client", FakeClient)
    monkeypatch.setattr(pd_tools, "get_settings",
                        lambda: SimpleNamespace(gcp_project="fake-project", bq_dataset="plant"))

    df = pd_tools.BigQueryPlantStore().capa_lots()

    assert df["date"].tolist() == ["2026-06-01"]
    assert all(isinstance(v, str) for v in df["date"])
    assert json.dumps(df.to_dict("records"))  # raises TypeError if still a date object


def test_list_plant_lots_covers_all_64_lots_with_every_parameter():
    lots = pd_tools.list_plant_lots()
    assert len(lots) == 64
    assert {lot.lot_id for lot in lots} >= {GOLDEN_LOT}
    golden = next(lot for lot in lots if lot.lot_id == GOLDEN_LOT)
    assert golden.defects_solder_bridge == 14
    assert golden.line == "L2"


def test_list_maintenance_covers_both_lines():
    events = pd_tools.list_maintenance()
    assert len(events) == 10
    assert {e.line for e in events} == {"L1", "L2"}
    wo388 = next(e for e in events if e.wo_id == "WO-388")
    assert wo388.post_check == "profile_verification_pending"


def test_reset_caches_clears_both_lru_caches():
    store_before = pd_tools.get_store()
    cached_before = pd_tools._joined_cached()

    pd_tools._reset_caches()

    store_after = pd_tools.get_store()
    cached_after = pd_tools._joined_cached()
    # Same backend/CSVs, so content is identical, but cache_clear() must force both
    # functions to rebuild — proven by object identity, not equal values. Identity is
    # asserted on the underlying cached function, not the public joined(), since
    # joined() now deliberately returns a new object on every call regardless of
    # whether the cache was cleared.
    assert store_after is not store_before
    assert cached_after is not cached_before
    assert cached_after.equals(cached_before)
