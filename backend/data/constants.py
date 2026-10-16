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

REFLOW_PEAK_LIMIT_C = 250.0        # profile limit drawn on the evidence chart
