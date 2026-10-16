import json

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
