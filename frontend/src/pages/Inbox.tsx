import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listComplaints } from "../api/client";
import type { Complaint } from "../api/types";

function humanizeDefect(s: string): string {
  const words = s.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function DueBadge({ days }: { days: number | null }) {
  if (days == null) return null;
  const urgent = days <= 3;
  return (
    <span
      className="mono text-xs font-semibold rounded-full px-2.5 py-1"
      style={{
        color: urgent ? "white" : "var(--ink)",
        background: urgent ? "var(--amber)" : "var(--line)",
      }}
    >
      8D due in {days} working day{days === 1 ? "" : "s"}
    </span>
  );
}

function RejectionBadge() {
  return (
    <span
      className="text-xs font-semibold rounded-full px-2.5 py-1 border"
      style={{ color: "var(--red)", borderColor: "var(--red)" }}
      title="The customer rejected the 8D already submitted for this complaint"
    >
      Rejected 8D
    </span>
  );
}

function ComplaintCard({ c, onOpen }: { c: Complaint; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="card p-4 text-left w-full flex flex-col gap-2 hover:shadow-sm transition-shadow focus-visible:outline-2"
    >
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <span className="text-sm font-semibold">{c.customer}</span>
        <DueBadge days={c.due_in_working_days} />
      </div>
      <p className="text-sm opacity-80">
        {c.product} · lot <span className="mono">{c.lot_id}</span>
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <p className="text-sm">
          <span className="font-medium">{humanizeDefect(c.defect)}</span>
          {c.qty_affected != null && c.qty_shipped != null && (
            <span className="opacity-70 mono">
              {" "}
              · {c.qty_affected} of {c.qty_shipped} units
            </span>
          )}
        </p>
        {c.is_rejection && <RejectionBadge />}
      </div>
      {c.is_rejection && c.objection && (
        <p className="text-xs opacity-70 italic">&ldquo;{c.objection}&rdquo;</p>
      )}
      <p className="mono text-xs opacity-50">{c.complaint_id}</p>
    </button>
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
    <div className="flex flex-col gap-8">
      <section>
        <div className="flex items-baseline justify-between gap-2 flex-wrap mb-3">
          <h1 className="text-lg font-semibold">Open complaints</h1>
          {open.length > 0 && (
            <span className="text-xs opacity-60">Sorted by 8D due date · most urgent first</span>
          )}
        </div>
        {open.length === 0 ? (
          <p className="text-sm opacity-60">No open complaints. Nice work.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {open.map((c) => (
              <ComplaintCard
                key={c.complaint_id}
                c={c}
                onOpen={() => navigate(`/new?complaint=${encodeURIComponent(c.complaint_id)}`)}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold mb-3 opacity-80">Past investigations</h2>
        {closed.length === 0 ? (
          <p className="text-sm opacity-60">No closed complaints yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {closed.map((c) => (
              <li key={c.complaint_id} className="card p-3 text-sm flex flex-wrap items-center gap-2 opacity-80">
                <span className="font-medium">{c.customer}</span>
                <span className="opacity-60">· {c.product} · lot {c.lot_id}</span>
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
