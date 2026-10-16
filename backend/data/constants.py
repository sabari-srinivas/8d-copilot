"""Single source of truth for the planted scenario. Imported by the generator,
the data gate and the statistics tool so their thresholds can never drift apart."""

SEED = 2612
OP17_L1_SHARE = 0.25           # tuned so H4 (operator OP-17) lands inconclusive, not supported
PRODUCT = "ECU-PCB-7"
PLANT = "Sree Electronics (fictional), Chennai"

START_DATE = "2026-09-14"
END_DATE = "2026-10-13"
WO388_ID = "WO-388"
WO388_DATE = "2026-10-08"      # reflow oven zone 7 heater replaced, profile verification pending
WO386_DATE = "2026-10-07"      # new stencil ST-07B installed on Line 2
OP17_START = "2026-10-06"

LOT_NUM_RANGE = (2551, 2615)                                   # 64 lots
DRIFT_LOT_IDS = [f"L{n}" for n in range(2609, 2615)]           # L2609-L2614, all Line 2
GOLDEN_LOT = "L2611"
GOLDEN_BRIDGES = 14                                            # matches complaint C-2026-031

DEFECT_RATE_THRESHOLD = 0.012      # a lot is a "defect lot" above this solder-bridge rate

# PRD 9.3: an effect must be meaningful, not merely significant.
MIN_EFFECT = {
    "reflow_peak_temp_c": 3.0,
    "time_above_liquidus_s": 5.0,
    "preheat_ramp_c_per_s": 0.3,
    "soak_time_s": 10.0,
    "conveyor_speed_cm_min": 3.0,
    "paste_age_h": 4.0,
    "room_humidity_pct": 5.0,
    "stencil_print_count": 5000.0,
    "squeegee_pressure_kg": 0.5,
    "operator_id": 0.15,           # difference in share of lots, 0-1
}

# stencil_id and paste_lot are deliberately NOT testable parameters: categorical
# stencil/paste identity is perfectly collinear with the WO-388 window (ST-07B was
# installed by WO-386 on 2026-10-07, one day before the oven heater work WO-388
# fixed on 2026-10-08 -- every drift lot carries both). classify() has no notion of
# confounding, so a bare categorical test on stencil_id returns a confident
# `supported` for a nuisance variable it cannot distinguish from the true cause.
# Test stencil wear through `stencil_print_count` instead, which correctly REJECTS
# on direction (a new stencil means FEWER prints, not more) -- the clearest
# demonstration of the direction-aware verdict rule. Do not re-add stencil_id or
# paste_lot here without first breaking that collinearity in the dataset.
PARAM_UNITS = {
    "reflow_peak_temp_c": "°C",
    "time_above_liquidus_s": "s",
    "preheat_ramp_c_per_s": "°C/s",
    "soak_time_s": "s",
    "conveyor_speed_cm_min": "cm/min",
    "paste_age_h": "h",
    "room_humidity_pct": "%RH",
    "stencil_print_count": "prints",
    "squeegee_pressure_kg": "kg",
    "operator_id": "share of lots",
}

# Parameters tested by counting which categorical level is over-represented
# (Fisher exact), rather than by comparing a numeric mean (Welch t-test).
# Single source of truth: agent/tools/plant_data.NUMERIC_PARAMS excludes this
# set, and agent/tools/stats_test.test_hypothesis routes on it.
CATEGORICAL_PARAMS = {"operator_id"}

# Human-readable names for effect strings shown in the live trace and the 8D.
# A parameter not listed here falls back to its column name with underscores
# turned to spaces (e.g. "reflow_peak_temp_c" -> "reflow peak temp c").
PARAM_LABELS = {
    "reflow_peak_temp_c": "reflow peak temperature",
    "time_above_liquidus_s": "time above liquidus",
    "preheat_ramp_c_per_s": "preheat ramp rate",
    "soak_time_s": "soak time",
    "conveyor_speed_cm_min": "conveyor speed",
    "paste_age_h": "paste age",
    "room_humidity_pct": "room humidity",
    "stencil_print_count": "stencil print count",
    "squeegee_pressure_kg": "squeegee pressure",
}

REFLOW_PEAK_LIMIT_C = 250.0        # profile limit drawn on the evidence chart
