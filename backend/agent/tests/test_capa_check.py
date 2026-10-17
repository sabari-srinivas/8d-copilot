"""agent/tools/capa_check.py -- did a past CAPA actually reduce the defect rate?
Hermetic: no plant CSVs, no LLM calls. Every scenario monkeypatches
get_capa_defect_series with a constructed DataFrame (lot_id, date, rate), so the exact
p-values and effect signs are known in advance (verified against scipy directly, see
.superpowers/sdd/2026-10-16-8d-copilot-prototype/capa-effectiveness-report.md).
"""
import pandas as pd
import pytest

from agent.state import MemoryStateStore
from agent.tools import capa_check

IMPLEMENTED_ON = "2026-07-10"


def _series(before, immediate, recent) -> pd.DataFrame:
    """Build a (lot_id, date, rate) frame: `before` dates <= IMPLEMENTED_ON, `immediate`
    the earliest lots after it, `recent` the latest -- exactly the chronological split
    verify_capa_effectiveness itself performs, so the caller controls which rates land
    in which window."""
    rows = []
    for i, rate in enumerate(before):
        rows.append(("L%d" % (100 + i), f"2026-07-{1 + i:02d}", rate))
    for i, rate in enumerate(immediate):
        rows.append(("L%d" % (200 + i), f"2026-07-{11 + i:02d}", rate))
    for i, rate in enumerate(recent):
        rows.append(("L%d" % (300 + i), f"2026-07-{20 + i:02d}", rate))
    df = pd.DataFrame(rows, columns=["lot_id", "date", "rate"])
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture
def stub(monkeypatch):
    def _install(df: pd.DataFrame):
        monkeypatch.setattr(capa_check, "get_capa_defect_series", lambda *a, **k: df)
    return _install


BEFORE_HIGH = [0.028, 0.031, 0.029, 0.030, 0.032, 0.027]     # ~2.9%, clearly defective
LOW = [0.005, 0.006, 0.004, 0.0055, 0.0045, 0.005]           # ~0.5%, well below LOW


def test_worked_when_the_drop_holds(stub):
    stub(_series(BEFORE_HIGH, LOW, LOW))
    result = capa_check.verify_capa_effectiveness("CAPA-T1", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "worked"
    assert result.p_value < 0.01
    assert result.effect_value < 0
    assert result.before_rate > result.recent_rate


def test_never_worked_when_nothing_changes(stub):
    flat = [0.027, 0.029, 0.030, 0.028, 0.031, 0.029]
    stub(_series(BEFORE_HIGH, flat, flat))
    result = capa_check.verify_capa_effectiveness("CAPA-T2", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "never_worked"
    assert result.p_value > 0.1


def test_regressed_when_the_drop_fades(stub):
    back_up = [0.028, 0.030, 0.029, 0.031, 0.027, 0.030]     # back near BEFORE_HIGH
    stub(_series(BEFORE_HIGH, LOW, back_up))
    result = capa_check.verify_capa_effectiveness("CAPA-T3", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "regressed"
    # The headline number is the recent-vs-before comparison -- the one that failed.
    assert result.p_value > 0.1


def test_a_rate_that_rose_is_never_worked_however_significant(stub):
    """Direction rule: classify() rejects a positive effect under direction='lower'
    regardless of the p-value. A CAPA whose immediate rate shot UP must never be
    reported as 'worked', even with an extremely significant p."""
    rose = [0.045, 0.048, 0.047, 0.046, 0.049, 0.044]        # far ABOVE before
    stub(_series(BEFORE_HIGH, rose, rose))
    result = capa_check.verify_capa_effectiveness("CAPA-T4", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "never_worked"
    assert result.verdict != "worked"
    assert result.effect_value > 0


def test_insufficient_data_when_a_window_is_too_small(stub):
    """Only two lots before the CAPA -- MIN_GROUP is 3. Never guess with this little."""
    stub(_series(BEFORE_HIGH[:2], LOW, LOW))
    result = capa_check.verify_capa_effectiveness("CAPA-T5", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "insufficient_data"
    assert result.p_value is None
    assert result.effect_value is None
    assert result.n_before == 2


def test_unknown_capa_has_no_lots_on_either_side(stub):
    """A capa_id/line nobody recognises: the data layer returns nothing at all, not a
    guess. Same insufficient_data verdict as a too-small window, reached with zero
    lots rather than a few."""
    empty = pd.DataFrame(columns=["lot_id", "date", "rate"])
    empty["date"] = pd.to_datetime(empty["date"])
    stub(empty)
    result = capa_check.verify_capa_effectiveness("CAPA-NOPE", "tombstoning", "L9",
                                                  IMPLEMENTED_ON)
    assert result.verdict == "insufficient_data"
    assert result.n_before == result.n_immediate == result.n_recent == 0


def test_group_sizes_and_labels_are_reported(stub):
    stub(_series(BEFORE_HIGH, LOW, LOW))
    result = capa_check.verify_capa_effectiveness("CAPA-T6", "tombstoning", "L1",
                                                  IMPLEMENTED_ON)
    assert result.n_before == 6
    assert result.n_immediate == 6
    assert result.n_recent == 6
    assert len(result.group_labels) == 3
    assert "CAPA-T6" in result.group_labels[0]


def test_the_real_seeded_historical_capa_never_worked():
    """End-to-end, real data: the historical CAPA-0098 seeded in data/generate_plant.py
    (tied to closed complaint C-2026-024) for exactly this demo. No monkeypatching --
    proves the seed data and get_capa_defect_series's historical-table path actually
    produce the documented verdict."""
    from data.constants import (HISTORICAL_CAPA_DEFECT_TYPE, HISTORICAL_CAPA_ID,
                                HISTORICAL_CAPA_IMPLEMENTED_ON, HISTORICAL_CAPA_LINE)
    result = capa_check.verify_capa_effectiveness(
        HISTORICAL_CAPA_ID, HISTORICAL_CAPA_DEFECT_TYPE, HISTORICAL_CAPA_LINE,
        HISTORICAL_CAPA_IMPLEMENTED_ON)
    assert result.verdict == "never_worked"
    assert result.n_before == 10 and result.n_immediate == 7 and result.n_recent == 7


@pytest.fixture
def local_state(monkeypatch):
    store = MemoryStateStore()
    monkeypatch.setattr(capa_check, "get_state", lambda: store)
    return store


def test_seeding_the_historical_capa_record(local_state):
    capa_id = capa_check.seed_historical_capa()
    assert capa_id == "CAPA-0098"
    record = local_state.get_record("capa", "CAPA-0098")
    assert record["status"] == "closed"
    assert record["lot_id"] == "L2389"


def test_seeding_the_historical_capa_twice_is_a_no_op(local_state):
    first = capa_check.seed_historical_capa()
    second = capa_check.seed_historical_capa()
    assert first == "CAPA-0098"
    assert second is None
    assert len(local_state.list_records("capa")) == 1


def test_seeding_the_historical_capa_never_consumes_the_live_counter(local_state):
    capa_check.seed_historical_capa()
    live_id = local_state.create_record("capa", {"summary": "live"})
    assert live_id == "CAPA-0142"
