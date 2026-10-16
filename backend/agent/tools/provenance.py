"""PRD 9.6: no number in the 8D that is not in a tool result.

A warning pass, not a hard gate — the investigation still finishes, but the violation is
emitted as a system event and shown in the UI so a human can see what to check.

`grounded_facts` is the single source of truth for what the writer is allowed to know:
the writer formats it into its prompt and `allowed_numbers` harvests the same dict, so
a number can never be in one and missing from the other.
"""
import logging
import re

import pandas as pd

from agent.models import Complaint, EightD, Investigation
from agent.tools.plant_data import get_lot_genealogy, get_maintenance_events, get_process_window, joined
from data.constants import REFLOW_PEAK_LIMIT_C

log = logging.getLogger(__name__)

NUMBER = re.compile(r"\d+(?:\.\d+)?")
# Dates, section labels and ordinary prose numbers that carry no factual claim.
ALWAYS_OK = {str(n) for n in range(0, 13)} | {"2026", "16949", "2019", "8"}

# The lot-level measurements the writer may quote. `shift` and `product` are read with
# row["..."] throughout — never attribute access, which collides with pandas methods.
LOT_FIELDS = ("lot_id", "line", "shift", "product", "operator_id")
LOT_NUMERIC = ("qty", "reflow_peak_temp_c", "time_above_liquidus_s",
               "defects_solder_bridge", "bridge_rate")
# The one parameter whose window statistics the 8D narrative turns on.
WINDOW_PARAM = "reflow_peak_temp_c"


def _variants(value) -> set[str]:
    text = str(value)
    out = {text}
    try:
        number = float(text)
        out |= {f"{number:g}", f"{number:.1f}", f"{number:.2f}", f"{number:.3f}",
                f"{int(number)}" if number.is_integer() else text,
                f"{number:,.0f}", f"{abs(number):g}"}
    except ValueError:
        pass
    return {v.lstrip("+") for v in out}


def _rate_variants(value: float) -> set[str]:
    """A rate between 0 and 1 is just as likely to be written as a percentage."""
    return _variants(value) | _variants(round(value * 100, 2))


def _lot_rows(lot_ids: list[str]) -> list[dict]:
    """The lots/process rows for the lots in play, as plain JSON-able dicts."""
    df = joined()
    df = df[df["lot_id"].isin(lot_ids)].sort_values("date")
    rows = []
    for _, row in df.iterrows():
        out = {field: str(row[field]) for field in LOT_FIELDS}
        out["date"] = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        out["qty"] = int(row["qty"])
        out["reflow_peak_temp_c"] = float(row["reflow_peak_temp_c"])
        out["time_above_liquidus_s"] = float(row["time_above_liquidus_s"])
        out["defects_solder_bridge"] = int(row["defects_solder_bridge"])
        out["bridge_rate"] = round(float(row["bridge_rate"]), 4)
        rows.append(out)
    return rows


def grounded_facts(inv: Investigation, complaint: Complaint | None = None) -> dict:
    """Every tool result the writer may draw a number from.

    Degrades to the parts it can compute: a lot that is not in the plant data (a
    hand-typed complaint, a dataset that has not been generated) yields no plant facts
    rather than an exception — the provenance pass is a warning, never a blocker.
    """
    lot_ids = [inv.lot_id, *inv.hold_lots] if inv.lot_id else list(inv.hold_lots)
    facts: dict = {
        "lot_id": inv.lot_id,
        "hold_lots": list(inv.hold_lots),
        "reflow_peak_limit_c": REFLOW_PEAK_LIMIT_C,
        "lots": [],
        "process_window": {},
        "peak_limit_breaches": {"n_lots": 0, "n_over_limit": 0, "lot_ids": []},
        "maintenance_events": [],
        "complaint": complaint.model_dump() if complaint else {},
    }
    if not lot_ids:
        return facts
    try:
        facts["lots"] = _lot_rows(lot_ids)
        window = get_process_window()
        facts["process_window"] = {
            "product": window["product"], "days": window["days"],
            "n_lots": window["n_lots"], WINDOW_PARAM: window["parameters"][WINDOW_PARAM]}
        # The breach count is over the lots on hold — the "affected window" the 8D
        # describes — not over every lot the query returned.
        window_lots = [row for row in facts["lots"] if row["lot_id"] in set(inv.hold_lots)]
        over = [row["lot_id"] for row in window_lots
                if row[WINDOW_PARAM] > REFLOW_PEAK_LIMIT_C]
        facts["peak_limit_breaches"] = {"n_lots": len(window_lots),
                                        "n_over_limit": len(over), "lot_ids": over}
        if inv.lot_id:
            facts["maintenance_events"] = get_maintenance_events(
                get_lot_genealogy(inv.lot_id)["line"])
    except (KeyError, IndexError, FileNotFoundError) as exc:
        log.warning("grounded_facts fell back to the narrow set: %s", exc.__class__.__name__)
    return facts


def _harvest(value, out: set[str]) -> None:
    """Collect every number reachable in a tool result, whatever its nesting."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        out |= _variants(value)
    elif isinstance(value, str):
        out |= set(NUMBER.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            _harvest(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _harvest(item, out)


def allowed_numbers(inv: Investigation, complaint: Complaint | None = None) -> set[str]:
    allowed: set[str] = set(ALWAYS_OK)
    for result in inv.results:
        for value in (result.p_value, result.effect_value, result.n_defect, result.n_good):
            allowed |= _variants(value)
        allowed |= set(NUMBER.findall(result.effect))
    for citation in inv.citations:
        allowed |= set(NUMBER.findall(f"{citation.label} {citation.ref} {citation.quote}"))
    for row in inv.traveler_rows:
        allowed |= set(NUMBER.findall(row.lot_id))
        for value in (row.reflow_peak_temp_c, row.time_above_liquidus_s, row.aoi_bridges):
            if value is not None:
                allowed |= _variants(value)
    allowed |= set(NUMBER.findall(inv.lot_id))
    if inv.defect:
        allowed |= _variants(round(inv.defect.confidence * 100))

    facts = grounded_facts(inv, complaint)
    _harvest(facts, allowed)
    for row in facts["lots"]:
        allowed |= _rate_variants(row["bridge_rate"])
    return allowed


def check_numbers(eight_d: EightD, allowed: set[str]) -> list[str]:
    violations: list[str] = []
    for name in (f"D{i}" for i in range(1, 9)):
        section = getattr(eight_d, name)
        cited = set()
        for citation in section.citations:
            cited |= set(NUMBER.findall(f"{citation.label} {citation.ref} {citation.quote}"))
        for found in NUMBER.findall(section.text):
            if found.lstrip("+") not in allowed and found not in cited:
                violations.append(f"{name}: {found} is not in any tool result")
    return violations
