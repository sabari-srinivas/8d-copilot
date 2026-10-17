"""Read-only rollups for GET /api/dashboard/summary and GET /api/capas. No LLM
touches this file -- every number here is a plain computation over the same
plant/state data agent/tools/plant_data.py and agent/tools/capa_check.py already
serve to the investigation flow, never a hard-coded figure. The planted scenario's
headline numbers (99.12% yield, 188 solder-bridge defects, Line 1 vs Line 2 drift)
are facts of data/generate_plant.py's current seed, not constants in this module --
regenerate the seed and these change with it.
"""
from agent.models import (CapaDashboardSummary, CapaRecord, DashboardCharts,
                          DashboardSummary, DefectPareto, DefectRateByLine,
                          DefectRateByLinePoint, FirstPassYield, OpenEightDs,
                          SpcPoint, SpcReflowPeak)
from agent.state import get_state
from agent.tools.capa_check import verify_capa_effectiveness
from agent.tools.intake_tools import list_complaints
from agent.tools.memory import list_quality_memory
from agent.tools.plant_data import joined
from data.constants import REFLOW_PEAK_LIMIT_C, WO388_DATE, WO388_ID


def get_first_pass_yield() -> FirstPassYield:
    df = joined()
    units = int(df.qty.sum())
    defects = int((df.defects_solder_bridge + df.defects_other).sum())
    pct = round(100 * (1 - defects / units), 2) if units else 0.0
    return FirstPassYield(units=units, defects=defects, pct=pct)


def get_open_eight_ds() -> OpenEightDs:
    open_complaints = [c for c in list_complaints() if c.status == "open"]
    due_days = [c.due_in_working_days for c in open_complaints if c.due_in_working_days is not None]
    return OpenEightDs(count=len(open_complaints),
                       soonest_due_working_days=min(due_days) if due_days else None)


def get_lots_on_hold() -> int:
    lots: set[str] = set()
    for h in get_state().list_records("hold"):
        if h.get("status") == "active":
            lots.update(h.get("lots") or [])
    return len(lots)


def list_capas_with_effectiveness() -> list[CapaRecord]:
    """Every CAPA record (live-approved or the seeded historical CAPA-0098), each
    joined to the quality-memory entry it produced (matched on capa_id -- the same
    linkage agent/agents/actions.py writes via save_quality_memory) for its
    defect_type/line, and -- only when both are known -- its effectiveness verdict
    from the SAME rule every other verdict in this product uses."""
    memory_by_capa = {m.capa_id: m for m in list_quality_memory() if m.capa_id}
    out: list[CapaRecord] = []
    for raw in get_state().list_records("capa"):
        mem = memory_by_capa.get(raw["id"])
        defect_type = mem.defect_type if mem else ""
        line = mem.line if mem else ""
        effectiveness = None
        if defect_type and line and raw.get("opened"):
            try:
                effectiveness = verify_capa_effectiveness(raw["id"], defect_type, line,
                                                          raw["opened"])
            except Exception:
                # Best-effort: a CAPA whose implementation date or history can't be
                # evaluated still shows up in the list, just without a verdict --
                # never guessed, never a reason to hide the record itself.
                effectiveness = None
        out.append(CapaRecord(**raw, defect_type=defect_type, line=line,
                              memory_id=mem.id if mem else "", effectiveness=effectiveness))
    return sorted(out, key=lambda c: c.opened, reverse=True)


def get_capa_summary() -> CapaDashboardSummary:
    capas = list_capas_with_effectiveness()
    open_count = sum(1 for c in capas if c.status == "open")
    determinate = [c.effectiveness for c in capas
                   if c.effectiveness is not None and c.effectiveness.verdict != "insufficient_data"]
    recurred = sum(1 for e in determinate if e.verdict in ("never_worked", "regressed"))
    recurrence_rate = round(recurred / len(determinate), 4) if determinate else None
    return CapaDashboardSummary(open=open_count, recurrence_rate=recurrence_rate,
                                n_evaluated=len(determinate))


def get_defect_pareto() -> DefectPareto:
    df = joined()
    return DefectPareto(solder_bridge=int(df.defects_solder_bridge.sum()),
                        other=int(df.defects_other.sum()))


def get_defect_rate_by_line() -> DefectRateByLine:
    df = joined().sort_values("date")

    def points(line: str) -> list[DefectRateByLinePoint]:
        sub = df[df.line == line]
        return [DefectRateByLinePoint(lot_id=r.lot_id, date=r.date.strftime("%Y-%m-%d"),
                                      rate_pct=round(float(r.bridge_rate) * 100, 3))
                for r in sub.itertuples()]

    l1, l2 = df[df.line == "L1"], df[df.line == "L2"]
    return DefectRateByLine(
        line1=points("L1"), line2=points("L2"),
        line1_avg_pct=round(float(l1.bridge_rate.mean()) * 100, 2) if len(l1) else 0.0,
        line2_avg_pct=round(float(l2.bridge_rate.mean()) * 100, 2) if len(l2) else 0.0,
        marker_date=WO388_DATE, marker_label=WO388_ID)


def get_spc_reflow_peak() -> SpcReflowPeak:
    df = joined().sort_values("date")
    points = [SpcPoint(lot_id=r.lot_id, date=r.date.strftime("%Y-%m-%d"),
                       value=round(float(r.reflow_peak_temp_c), 2)) for r in df.itertuples()]
    return SpcReflowPeak(limit_c=REFLOW_PEAK_LIMIT_C, points=points)


def get_dashboard_summary() -> DashboardSummary:
    return DashboardSummary(
        first_pass_yield=get_first_pass_yield(),
        open_eight_ds=get_open_eight_ds(),
        capas=get_capa_summary(),
        lots_on_hold=get_lots_on_hold(),
        charts=DashboardCharts(
            defect_rate_by_line=get_defect_rate_by_line(),
            defect_pareto=get_defect_pareto(),
            spc_reflow_peak=get_spc_reflow_peak(),
        ),
    )
