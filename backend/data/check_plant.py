"""check_plant.py — the planted cause must be detectable and the decoys must not be.
Uses the SAME verdict rule the agent uses at runtime (agent/tools/stats_verdict.classify),
so the data gate and the product can never disagree.

Exit 0 = the dataset is demo-ready. Exit 1 = regenerate or retune.
"""
import sys
from pathlib import Path
import pandas as pd
from scipy import stats

from data.constants import (DEFECT_RATE_THRESHOLD, DRIFT_LOT_IDS, GOLDEN_BRIDGES,
                            GOLDEN_LOT, MIN_EFFECT, PARAM_UNITS, WO388_DATE)
from agent.tools.stats_verdict import classify

OUT = Path(__file__).parent / "out"
lots = pd.read_csv(OUT / "lots.csv")
df = lots.merge(pd.read_csv(OUT / "process.csv"), on="lot_id")
df["bridge_rate"] = df.defects_solder_bridge / df.qty
bad = df.bridge_rate > DEFECT_RATE_THRESHOLD

CASES = [
    # id,  description,                              column,                  direction, required
    ("H2", "Reflow peak temp drift (L2, WO-388)",    "reflow_peak_temp_c",    "higher", "supported"),
    ("H2b", "Time above liquidus",                   "time_above_liquidus_s", "higher", "supported"),
    ("H1", "Stencil wear (print count)",             "stencil_print_count",   "higher", "rejected"),
    ("H3", "Room humidity",                          "room_humidity_pct",     "higher", "rejected"),
    ("H5", "Paste age",                              "paste_age_h",           "higher", "rejected"),
]

failures: list[str] = []
print(f"defect lots ({int(bad.sum())}): {sorted(df[bad].lot_id)}\n")
print(f"{'id':5}{'hypothesis':40}{'test':10}{'p':>9}  {'effect':>14}  {'verdict':13}required")

for hid, name, col, direction, required in CASES:
    _, p = stats.ttest_ind(df[bad][col], df[~bad][col], equal_var=False)
    eff = float(df[bad][col].mean() - df[~bad][col].mean())
    got = classify(p, eff, direction, MIN_EFFECT[col])
    flag = "" if got == required else "   <-- FAIL"
    print(f"{hid:5}{name:40}{'Welch t':10}{p:9.4f}  {eff:+10.1f} {PARAM_UNITS[col]:<4} {got:13}{required}{flag}")
    if got != required:
        failures.append(f"{hid} ({name}): got {got}, required {required}, p={p:.4f}, effect={eff:+.1f}")

# H4 operator: share of OP-17 lots among defect vs good lots, Fisher exact.
tab = pd.crosstab(df.operator_id == "OP-17", bad)
_, p4 = stats.fisher_exact(tab.values)
share_bad = float((df[bad].operator_id == "OP-17").mean())
share_good = float((df[~bad].operator_id == "OP-17").mean())
eff4 = share_bad - share_good
got4 = classify(p4, eff4, "higher", MIN_EFFECT["operator_id"])
flag = "" if got4 == "inconclusive" else "   <-- FAIL"
print(f"{'H4':5}{'Operator change (OP-17)':40}{'Fisher':10}{p4:9.4f}  {eff4:+10.2f} {'share':<4} {got4:13}inconclusive{flag}")
if got4 != "inconclusive":
    failures.append(f"H4 operator: got {got4}, required inconclusive, p={p4:.4f}. "
                    f"Retune with --op17-l1-share until Fisher p lands in 0.01..0.1.")

# Structural invariants the demo and the 8D depend on.
checks = {
    "defect lots are exactly the drift lots":
        sorted(df[bad].lot_id) == sorted(DRIFT_LOT_IDS),
    f"{GOLDEN_LOT} has exactly {GOLDEN_BRIDGES} bridges (matches complaint C-2026-031)":
        int(df.loc[df.lot_id == GOLDEN_LOT, "defects_solder_bridge"].iloc[0]) == GOLDEN_BRIDGES,
    "no Line 2 lot after WO-388 outside the drift window":
        sorted(df[(df.line == "L2") & (pd.to_datetime(df.date) > pd.Timestamp(WO388_DATE))].lot_id)
        == sorted(DRIFT_LOT_IDS),
    "drift lots exceed the 250 C profile limit on average":
        float(df[df.lot_id.isin(DRIFT_LOT_IDS)].reflow_peak_temp_c.mean()) > 250.0,
}
print()
for name, ok in checks.items():
    print(f"[{'ok' if ok else 'FAIL'}] {name}")
    if not ok:
        failures.append(name)

if failures:
    print("\nFAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nAll required verdicts and invariants hold. Dataset is demo-ready.")
