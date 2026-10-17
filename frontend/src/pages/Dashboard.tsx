import { ArrowRight, Boxes, ClipboardCheck, Gauge, Inbox as InboxIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboardSummary } from "../api/client";
import type { DashboardSummary } from "../api/types";
import { DefectRateChart } from "../components/DefectRateChart";
import { LifecycleStrip } from "../components/LifecycleStrip";
import { ParetoChart } from "../components/ParetoChart";
import { SpcChart } from "../components/SpcChart";

/** One KPI tile. "Every number on the dashboard is a door" — each tile is a link to
 * the tab that explains it (open 8Ds -> Complaints, recurrence rate -> CAPA, yield ->
 * Plant), never a dead-end number. Amber is reserved for the warning case on that
 * specific tile (a soon-due 8D, a nonzero recurrence rate, a lot genuinely on hold) —
 * never decorative. */
function KpiTile({
  to, icon: Icon, label, value, sub, tone,
}: {
  to: string;
  icon: typeof InboxIcon;
  label: string;
  value: string;
  sub?: string;
  tone?: "amber";
}) {
  return (
    <Link
      to={to}
      className="card card-interactive group flex flex-col gap-1.5 px-4 py-3.5 focus-visible:outline-2"
    >
      <span className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 stat-label" style={{ color: tone === "amber" ? "var(--amber-ink)" : undefined }}>
          <Icon size={13} aria-hidden="true" />
          {label}
        </span>
        <ArrowRight size={14} className="opacity-0 group-hover:opacity-60 transition-opacity shrink-0" aria-hidden="true" />
      </span>
      <span className="mono text-2xl font-semibold leading-none" style={{ color: tone === "amber" ? "var(--amber-ink)" : undefined }}>
        {value}
      </span>
      {sub && <span className="text-xs opacity-70">{sub}</span>}
    </Link>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card p-4 flex flex-col gap-1">
      <h2 className="text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

/** Route "/" — the dashboard landing page: see the state before picking the work.
 * Four KPI tiles (each a door into the tab that explains it), then three charts —
 * the hero defect-rate-by-line drift, the defect Pareto, and the reflow-peak SPC
 * chart. Deliberately no operator/shift breakdown tile: the data exists (Plant tab),
 * but a dashboard tile implying "which operator causes defects" cuts against this
 * product's own rule that operator error is never a root cause. */
export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary().then(setSummary);
  }, []);

  if (!summary) {
    return <p className="text-sm opacity-60">Loading dashboard…</p>;
  }

  const { first_pass_yield, open_eight_ds, capas, lots_on_hold, charts } = summary;
  const soonestUrgent = open_eight_ds.soonest_due_working_days != null && open_eight_ds.soonest_due_working_days <= 3;
  const recurrencePct = capas.recurrence_rate == null ? null : Math.round(capas.recurrence_rate * 100);

  return (
    <div className="flex flex-col gap-5">
      <LifecycleStrip current="Dashboard" />
      <div>
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-sm opacity-70">
          Sree Electronics, Chennai · ECU-PCB-7 · computed from lot data, updated live.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
        <KpiTile
          to="/plant"
          icon={Gauge}
          label="First-pass yield"
          value={`${first_pass_yield.pct.toFixed(2)}%`}
          sub={`${first_pass_yield.units.toLocaleString()} units · ${first_pass_yield.defects} defects`}
        />
        <KpiTile
          to="/complaints"
          icon={InboxIcon}
          label="Open 8Ds"
          value={String(open_eight_ds.count)}
          sub={
            open_eight_ds.soonest_due_working_days == null
              ? "no 8Ds due"
              : `soonest due in ${open_eight_ds.soonest_due_working_days} working day${open_eight_ds.soonest_due_working_days === 1 ? "" : "s"}`
          }
          tone={soonestUrgent ? "amber" : undefined}
        />
        <KpiTile
          to="/capa"
          icon={ClipboardCheck}
          label="Open CAPAs"
          value={String(capas.open)}
          sub={
            recurrencePct == null
              ? "recurrence rate: not enough history yet"
              : `recurrence rate ${recurrencePct}% (${capas.n_evaluated} evaluated)`
          }
          tone={recurrencePct != null && recurrencePct > 0 ? "amber" : undefined}
        />
        <KpiTile
          to="/plant"
          icon={Boxes}
          label="Lots on hold"
          value={String(lots_on_hold)}
          sub={lots_on_hold > 0 ? "awaiting release" : "none held"}
          tone={lots_on_hold > 0 ? "amber" : undefined}
        />
      </div>

      <ChartCard title="Defect rate by lot — Line 1 vs Line 2">
        <DefectRateChart data={charts.defect_rate_by_line} />
      </ChartCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Defect Pareto">
          <ParetoChart data={charts.defect_pareto} />
        </ChartCard>
        <ChartCard title="Reflow peak temperature (SPC)">
          <SpcChart data={charts.spc_reflow_peak} />
        </ChartCard>
      </div>
    </div>
  );
}
