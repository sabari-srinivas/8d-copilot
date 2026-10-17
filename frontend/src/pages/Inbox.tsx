import { AlertCircle, Clock, Inbox as InboxIcon, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listComplaints } from "../api/client";
import type { Complaint } from "../api/types";

function humanizeDefect(s: string): string {
  const words = s.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The due-date countdown — the visual anchor of a row (CR brief: a quality engineer
 * works to deadlines). Urgent (<=3 working days) uses amber, reserved for warnings —
 * never decorative — with a dark foreground so it clears 4.5:1 in both themes (a plain
 * white label on this amber fails contrast; see visual-redesign-report.md). */
function DueBadge({ days }: { days: number | null }) {
  if (days == null) return null;
  const urgent = days <= 3;
  return (
    <span
      className="mono shrink-0 inline-flex items-center gap-1 text-sm font-semibold rounded-md px-2.5 py-1.5 whitespace-nowrap"
      style={{
        color: urgent ? "var(--pill-fg-amber)" : "var(--ink)",
        background: urgent ? "var(--amber)" : "var(--surface-sunken)",
      }}
    >
      {urgent && <Clock size={13} strokeWidth={2.5} aria-hidden="true" />}
      {days}d
      <span className="font-normal opacity-80 hidden sm:inline">to 8D due</span>
    </span>
  );
}

function RejectionBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold rounded-md px-2 py-0.5 border shrink-0"
      style={{ color: "var(--red)", borderColor: "var(--red)" }}
      title="The customer rejected the 8D already submitted for this complaint"
    >
      <RotateCcw size={11} aria-hidden="true" />
      Rejected 8D
    </span>
  );
}

/** One open complaint, as a dense row rather than a padded card — an operator scans
 * many of these at once. The due countdown sits first, largest and boldest: it is
 * what decides what Priya works on next. */
function ComplaintRow({ c, onOpen }: { c: Complaint; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="card card-interactive text-left w-full flex items-start gap-3 px-3 py-2.5 focus-visible:outline-2"
    >
      <DueBadge days={c.due_in_working_days} />
      <div className="min-w-0 flex-1 flex flex-col gap-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold truncate">{c.customer}</span>
          <span className="text-xs opacity-60">{c.product}</span>
          {c.is_rejection && <RejectionBadge />}
        </div>
        <p className="text-sm">
          <span>{humanizeDefect(c.defect)}</span>
          <span className="opacity-60"> · lot </span>
          <span className="mono">{c.lot_id}</span>
          {c.qty_affected != null && c.qty_shipped != null && (
            <span className="opacity-60 mono"> · {c.qty_affected}/{c.qty_shipped} units</span>
          )}
        </p>
        {c.is_rejection && c.objection && (
          <p className="text-xs opacity-70 italic truncate">&ldquo;{c.objection}&rdquo;</p>
        )}
      </div>
      <span className="mono text-[11px] opacity-40 shrink-0 pt-0.5">{c.complaint_id}</span>
    </button>
  );
}

/** Top-of-screen KPI strip — five complaints is a dashboard, not a list. Three
 * numbers an operator checks first thing: how much is open, how soon the next one
 * is due, and how many are customer rejections (the ones that must not slip again). */
function KpiStrip({ open }: { open: Complaint[] }) {
  const soonest = open.reduce<number | null>((min, c) => {
    if (c.due_in_working_days == null) return min;
    return min == null ? c.due_in_working_days : Math.min(min, c.due_in_working_days);
  }, null);
  const rejections = open.filter((c) => c.is_rejection).length;

  const tiles: Array<{ label: string; value: string; Icon: typeof InboxIcon; tone?: "amber" }> = [
    { label: "Open complaints", value: String(open.length), Icon: InboxIcon },
    {
      label: "Soonest 8D due",
      value: soonest == null ? "—" : `${soonest}d`,
      Icon: Clock,
      tone: soonest != null && soonest <= 3 ? "amber" : undefined,
    },
    { label: "Rejections outstanding", value: String(rejections), Icon: AlertCircle, tone: rejections > 0 ? "amber" : undefined },
  ];

  return (
    <div className="grid grid-cols-3 gap-2 sm:gap-3">
      {tiles.map((t) => (
        <div key={t.label} className="card px-3 py-2.5 flex flex-col gap-1">
          <span className="flex items-center gap-1.5 stat-label" style={{ color: t.tone === "amber" ? "var(--amber-ink)" : undefined }}>
            <t.Icon size={12} aria-hidden="true" />
            {t.label}
          </span>
          <span
            className="mono text-xl font-semibold leading-none"
            style={{ color: t.tone === "amber" ? "var(--amber-ink)" : undefined }}
          >
            {t.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Ascending by due-date urgency, undated complaints last among the open ones (CR #7
 * — a quality engineer works to deadlines, so this matches the job better than
 * newest-first). The caller is responsible for already having split open from closed. */
function byUrgency(a: Complaint, b: Complaint): number {
  if (a.due_in_working_days == null) return b.due_in_working_days == null ? 0 : 1;
  if (b.due_in_working_days == null) return -1;
  return a.due_in_working_days - b.due_in_working_days;
}

/** Route "/" — one card per open complaint needing an 8D, plus a quiet list of
 * past investigations below. Tapping an open card starts a new investigation. */
export function Inbox() {
  const [complaints, setComplaints] = useState<Complaint[] | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    listComplaints().then(setComplaints);
  }, []);

  if (!complaints) {
    return <p className="text-sm opacity-60">Loading complaints…</p>;
  }

  const open = complaints.filter((c) => c.status === "open").sort(byUrgency);
  const closed = complaints.filter((c) => c.status === "closed");

  return (
    <div className="flex flex-col gap-5">
      <KpiStrip open={open} />

      <section>
        <div className="flex items-baseline justify-between gap-2 flex-wrap mb-2">
          <h1 className="text-lg font-semibold">Open complaints</h1>
          {open.length > 0 && (
            <span className="text-xs opacity-60">Sorted by 8D due date · most urgent first</span>
          )}
        </div>
        {open.length === 0 ? (
          <p className="text-sm opacity-60">No open complaints. Nice work.</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {open.map((c) => (
              <ComplaintRow
                key={c.complaint_id}
                c={c}
                onOpen={() => navigate(`/new?complaint=${encodeURIComponent(c.complaint_id)}`)}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold mb-2 opacity-80">Past investigations</h2>
        {closed.length === 0 ? (
          <p className="text-sm opacity-60">No closed complaints yet.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {closed.map((c) => (
              <li key={c.complaint_id} className="card px-3 py-2 text-sm flex flex-wrap items-center gap-2 opacity-75">
                <span className="font-medium">{c.customer}</span>
                <span className="opacity-60">· {c.product} · lot <span className="mono">{c.lot_id}</span></span>
                <span className="mono text-xs opacity-50 ml-auto">{c.complaint_id} · closed</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link to="/memory" className="tap-target inline-flex items-center text-sm font-medium underline w-fit" style={{ color: "var(--green)" }}>
        View quality memory →
      </Link>
    </div>
  );
}
