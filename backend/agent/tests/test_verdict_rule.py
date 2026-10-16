import pytest
from data.constants import MIN_EFFECT
from agent.tools.stats_verdict import classify


def test_supported_needs_significance_direction_and_size():
    assert classify(p_value=0.0001, effect=+8.2, direction="higher",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "supported"


def test_opposite_direction_is_rejected_however_significant():
    """H1 stencil wear: a NEW stencil means the defect lots have FEWER prints.
    A p-only rule would call this supported. The direction rule rejects it."""
    assert classify(p_value=1e-9, effect=-38400.0, direction="higher",
                    min_effect=MIN_EFFECT["stencil_print_count"]) == "rejected"


def test_lower_direction_rejects_a_positive_effect():
    assert classify(p_value=1e-9, effect=+5.0, direction="lower", min_effect=1.0) == "rejected"


def test_high_p_value_is_rejected():
    assert classify(p_value=0.62, effect=+0.4, direction="higher",
                    min_effect=MIN_EFFECT["room_humidity_pct"]) == "rejected"


def test_middle_p_value_is_inconclusive():
    assert classify(p_value=0.041, effect=+0.52, direction="higher",
                    min_effect=MIN_EFFECT["operator_id"]) == "inconclusive"


def test_significant_but_trivial_effect_is_inconclusive():
    assert classify(p_value=0.0001, effect=+1.1, direction="higher",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "inconclusive"


def test_direction_any_ignores_sign():
    assert classify(p_value=0.0001, effect=-8.2, direction="any",
                    min_effect=MIN_EFFECT["reflow_peak_temp_c"]) == "supported"


@pytest.mark.parametrize("p", [0.01, 0.1])
def test_boundaries_are_not_supported(p):
    assert classify(p_value=p, effect=+8.2, direction="higher", min_effect=3.0) != "supported"
