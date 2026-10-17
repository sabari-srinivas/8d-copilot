"""agent/tools/dashboard.py -- every number computed live from plant/state data, never
hard-coded. Where this test's assertions quote a specific figure (99.12% yield, 188
solder-bridge defects, Line 1/Line 2 averages), it is restating a FACT of the current
data/generate_plant.py seed as a regression check, not asserting a constant the
production code is allowed to shortcut to -- see data/check_plant.py for the parallel
convention on the hypothesis side.
"""
import pytest

from agent.state import MemoryStateStore
from agent.tools import capa_check, dashboard
from agent.tools import memory as mem_tool


@pytest.fixture(autouse=True)
def shared_store(monkeypatch):
    """dashboard.py, agent.tools.memory and agent.tools.capa_check each hold their own
    `get_state` reference (bound at import time) -- all three must be pointed at the
    SAME fresh store for a CAPA created in one to be visible to a lookup in another,
    the same pattern test_memory.py and test_capa_check.py already use."""
    store = MemoryStateStore()
    monkeypatch.setattr(dashboard, "get_state", lambda: store)
    monkeypatch.setattr(mem_tool, "get_state", lambda: store)
    monkeypatch.setattr(capa_check, "get_state", lambda: store)
    monkeypatch.setattr(mem_tool, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    return store


def test_first_pass_yield_matches_the_seeded_dataset():
    y = dashboard.get_first_pass_yield()
    assert y.units == 31973
    assert y.defects == 282
    assert y.pct == 99.12


def test_defect_pareto_matches_the_seeded_dataset():
    p = dashboard.get_defect_pareto()
    assert p.solder_bridge == 188
    assert p.other == 94


def test_defect_rate_by_line_shows_line2_worse_than_line1():
    chart = dashboard.get_defect_rate_by_line()
    assert chart.line1_avg_pct == 0.41
    assert chart.line2_avg_pct == 0.76
    assert chart.line2_avg_pct > chart.line1_avg_pct
    assert chart.marker_label == "WO-388"
    assert len(chart.line1) + len(chart.line2) == 64


def test_spc_reflow_peak_carries_the_250c_limit_across_all_lots():
    spc = dashboard.get_spc_reflow_peak()
    assert spc.limit_c == 250.0
    assert len(spc.points) == 64


def test_open_eight_ds_counts_the_five_open_complaints():
    o = dashboard.get_open_eight_ds()
    assert o.count == 5
    assert o.soonest_due_working_days is not None


def test_lots_on_hold_counts_distinct_lots_in_active_holds(shared_store):
    shared_store.create_record("hold", {"lots": ["L2609", "L2610"], "status": "active"})
    shared_store.create_record("hold", {"lots": ["L2610", "L2611"], "status": "active"})
    shared_store.create_record("hold", {"lots": ["L2612"], "status": "released"})
    assert dashboard.get_lots_on_hold() == 3


def test_lots_on_hold_is_zero_with_no_holds():
    assert dashboard.get_lots_on_hold() == 0


def test_capas_list_includes_the_seeded_historical_capa_with_its_verdict():
    capa_check.seed_historical_capa()
    mem_tool.seed_historical_quality_memory()
    capas = dashboard.list_capas_with_effectiveness()
    hist = next(c for c in capas if c.id == "CAPA-0098")
    assert hist.defect_type == "tombstoning"
    assert hist.line == "L1"
    assert hist.memory_id == "MEM-0098"
    assert hist.effectiveness is not None
    assert hist.effectiveness.verdict == "never_worked"


def test_capa_with_no_matching_memory_entry_has_no_effectiveness(shared_store):
    shared_store.create_record("capa", {"opened": "2026-10-16", "status": "open"})
    capas = dashboard.list_capas_with_effectiveness()
    assert len(capas) == 1
    assert capas[0].defect_type == ""
    assert capas[0].effectiveness is None


def test_capa_summary_recurrence_rate_reflects_the_never_worked_historical_capa():
    capa_check.seed_historical_capa()
    mem_tool.seed_historical_quality_memory()
    summary = dashboard.get_capa_summary()
    assert summary.n_evaluated == 1
    assert summary.recurrence_rate == 1.0
    assert summary.open == 0   # the historical CAPA is seeded "closed"


def test_capa_summary_recurrence_rate_is_none_with_no_determinate_verdicts():
    summary = dashboard.get_capa_summary()
    assert summary.n_evaluated == 0
    assert summary.recurrence_rate is None


def test_dashboard_summary_assembles_every_section():
    summary = dashboard.get_dashboard_summary()
    assert summary.first_pass_yield.units == 31973
    assert summary.open_eight_ds.count == 5
    assert summary.lots_on_hold == 0
    assert len(summary.charts.spc_reflow_peak.points) == 64
    assert summary.charts.defect_pareto.solder_bridge == 188
