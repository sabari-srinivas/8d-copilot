"""Charts come from the data, never from the model."""
import hashlib
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agent.tools.plant_data import joined
from agent.tools.storage import put_bytes
from data.constants import REFLOW_PEAK_LIMIT_C

GREEN, GREY, AMBER, RED = "#1b5e3f", "#9aa5a0", "#b7791f", "#a6281f"


def render_reflow_chart(defect_lots: list[str], event_date: str | None = None,
                        event_label: str = "") -> str:
    df = joined().sort_values("date")
    key_src = f"{sorted(defect_lots)}|{event_date}|{event_label}".encode()
    key = f"charts/reflow_{hashlib.sha1(key_src).hexdigest()[:10]}.png"

    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=160)
    for line, colour, marker in (("L1", GREY, "o"), ("L2", GREEN, "s")):
        sub = df[df.line == line]
        ax.plot(sub.date, sub.reflow_peak_temp_c, marker, ms=4.5, lw=0,
                color=colour, label=f"Line {line[-1]}")

    bad = df[df.lot_id.isin(defect_lots)]
    ax.plot(bad.date, bad.reflow_peak_temp_c, "s", ms=9, mfc="none", mec=RED, mew=1.6,
            lw=0, label="Defect lots")

    ax.axhline(REFLOW_PEAK_LIMIT_C, color=AMBER, ls="--", lw=1.2)
    ax.annotate(f"{REFLOW_PEAK_LIMIT_C:.0f} °C profile limit",
                xy=(df.date.min(), REFLOW_PEAK_LIMIT_C), xytext=(0, 4),
                textcoords="offset points", color=AMBER, fontsize=8)
    if event_date:
        ax.axvline(pd.Timestamp(event_date), color=RED, ls=":", lw=1.4)
        ax.annotate(event_label or event_date, xy=(pd.Timestamp(event_date), ax.get_ylim()[1]),
                    xytext=(4, -12), textcoords="offset points", color=RED, fontsize=8)

    ax.set_ylabel("Reflow peak temp (°C)", fontsize=9)
    ax.set_xlabel("Lot date", fontsize=9)
    ax.set_title("Reflow peak temperature by lot — synthetic demo data", fontsize=10)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower left")
    ax.grid(alpha=0.25, lw=0.6)
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return put_bytes(buf.getvalue(), key, "image/png")
