import pytest
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT, WO388_ID
from agent.tools.stats_test import test_hypothesis

# pytest's default collector walks every name in this module matching `test_*`,
# including names that merely arrived via import. Without this, pytest tries to
# collect the imported `test_hypothesis` function itself as a test case and errors
# on "fixture 'hypothesis_id' not found" -- it is a function under test, not a test.
test_hypothesis.__test__ = False


@pytest.fixture(scope="module")
def h2():
    return test_hypothesis("H2", GOLDEN_LOT, parameter="reflow_peak_temp_c",
                           event_wo_id=WO388_ID, direction="higher")


def test_h2_reflow_drift_is_supported(h2):
    assert h2.verdict == "supported"
    assert h2.p_value < 0.01
    assert h2.effect_value > 3.0
    assert h2.effect_unit == "°C"
    assert h2.test.startswith("Welch")


def test_h2_reports_group_sizes_and_a_chart(h2):
    assert h2.n_defect == len(DRIFT_LOT_IDS)
    # H2 is an event hypothesis: the comparison is same-line (Line 2 only, per
    # stats_test.py's documented design -- mixing in Line 1's separate reflow oven
    # would invalidate the before/after labels and the Welch t-test). Line 2 has 33
    # lots total, 6 of them after WO-388 (== the drift lots), so "before" is
    # deterministically 27. That number comes from the Task-1-verified dataset, not
    # a tunable threshold, so this asserts a real control group exists rather than
    # a specific count that would make the test data-shape-dependent.
    assert h2.n_good > 20
    assert h2.chart_url and h2.chart_url.endswith(".png")


def test_h2_effect_string_carries_sign_and_unit(h2):
    assert h2.effect.startswith("+") and "°C" in h2.effect


def test_h1_stencil_wear_is_rejected_on_direction():
    r = test_hypothesis("H1", GOLDEN_LOT, parameter="stencil_print_count", direction="higher")
    assert r.verdict == "rejected"
    assert r.effect_value < 0


def test_h3_humidity_is_rejected():
    r = test_hypothesis("H3", GOLDEN_LOT, parameter="room_humidity_pct", direction="higher")
    assert r.verdict == "rejected"


def test_h4_operator_is_inconclusive_and_uses_fisher():
    r = test_hypothesis("H4", GOLDEN_LOT, parameter="operator_id", direction="higher")
    assert r.verdict == "inconclusive"
    assert r.test == "Fisher exact"
    assert 0.01 <= r.p_value <= 0.1


def test_paste_age_is_rejected():
    r = test_hypothesis("H5", GOLDEN_LOT, parameter="paste_age_h", direction="higher")
    assert r.verdict == "rejected"


def test_event_only_hypothesis_defaults_to_the_reflow_parameter():
    r = test_hypothesis("H6", GOLDEN_LOT, event_wo_id=WO388_ID, direction="higher")
    assert r.verdict == "supported"
    assert "before" in " ".join(r.group_labels).lower()


def test_unknown_parameter_raises():
    with pytest.raises(ValueError, match="not a testable parameter"):
        test_hypothesis("H7", GOLDEN_LOT, parameter="vibes", direction="higher")


def test_no_parameter_and_no_event_raises():
    with pytest.raises(ValueError, match="parameter or event"):
        test_hypothesis("H8", GOLDEN_LOT)


def test_stencil_identity_is_not_testable_only_print_count_is():
    """stencil_id is deliberately excluded from PARAM_UNITS/CATEGORICAL_PARAMS
    (see data/constants.py): ST-07B (installed by WO-386, 2026-10-07) is perfectly
    collinear with the WO-388 window (2026-10-08) -- every drift lot carries both,
    so a bare categorical test on stencil_id cannot distinguish "the new stencil
    caused the defects" from "the new stencil happened to be installed the day
    before the oven was serviced." classify() has no notion of confounding and
    would return a confident `supported` for that nuisance variable if asked.
    Stencil wear is instead tested through the numeric stencil_print_count, which
    correctly REJECTS on direction (a new stencil means FEWER prints, not more) --
    the clearest demonstration of the direction-aware rule."""
    with pytest.raises(ValueError, match="not a testable parameter"):
        test_hypothesis("H9", GOLDEN_LOT, parameter="stencil_id", direction="higher")

    r = test_hypothesis("H9b", GOLDEN_LOT, parameter="stencil_print_count", direction="higher")
    assert r.verdict == "rejected"


def test_categorical_comparison_is_scoped_to_good_lots_not_the_whole_plant():
    """_categorical must restrict its 'good' side to get_comparison_groups'
    good_lots (same product, last 30 days), mirroring _numeric -- not every
    non-defect row in joined(). n_good should equal the known good-lot count (58),
    not the much larger unscoped complement."""
    r = test_hypothesis("H4", GOLDEN_LOT, parameter="operator_id", direction="higher")
    from agent.tools.plant_data import get_comparison_groups
    assert r.n_good == len(get_comparison_groups(GOLDEN_LOT)["good_lots"])


def test_unknown_maintenance_event_raises():
    with pytest.raises(ValueError, match="no maintenance event"):
        test_hypothesis("H10", GOLDEN_LOT, event_wo_id="WO-9999", direction="higher")


def test_event_too_close_to_the_data_boundary_raises():
    """WO-392 (2026-10-12) is the last Line 2 maintenance event, one day before the
    dataset's last lot date -- only 1 lot falls after it, so the Welch comparison
    does not have enough lots on that side to run."""
    with pytest.raises(ValueError, match="not enough lots"):
        test_hypothesis("H11", GOLDEN_LOT, event_wo_id="WO-392", direction="higher")
