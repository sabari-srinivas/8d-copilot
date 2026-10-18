import { Info } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listCapas } from "../api/client";
import type { CapaRecord } from "../api/types";
import { CapaVerdictPill } from "../components/CapaVerdictPill";
import { LifecycleStrip } from "../components/LifecycleStrip";

function humanize(s: string): string {
  if (!s) return "";
  const words = s.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Every other CAPA raised against the same complaint, oldest first.
 *
 * Exported for the test: the grouping, not the wording, is what must stay correct. */
export function siblingsOnSameComplaint(capa: CapaRecord, all: CapaRecord[]): CapaRecord[] {
  if (!capa.complaint_id) return [];
  return all
    .filter((c) => c.complaint_id === capa.complaint_id && c.id !== capa.id)
    .sort((a, b) => (a.opened || "").localeCompare(b.opened || ""));
}

/** Says plainly why two CAPAs on this screen can look almost identical (CR #19).
 *
 * They are not duplicates and not a bug: the same complaint was investigated twice, on
 * different days, and each approval correctly opened its own CAPA. Left unexplained,
 * two near-identical open rows read as a duplicate-detection failure — the worst
 * possible misreading of a product whose claim is that quality memory stops recurrence.
 *
 * Computed from the records rather than hard-coded to a pair of ids, so it tells the
 * truth about whatever is actually in the store, and disappears by itself once there is
 * only one CAPA per complaint. */
function SameComplaintNote({ capa, siblings }: { capa: CapaRecord; siblings: CapaRecord[] }) {
  if (siblings.length === 0) return null;
  const ordered = [capa, ...siblings].sort((a, b) =>
    (a.opened || "").localeCompare(b.opened || ""));
  const position = ordered.findIndex((c) => c.id === capa.id) + 1;

  return (
    <p
      className="flex items-start gap-2 text-xs rounded-md px-2.5 py-2"
      style={{ background: "var(--amber-soft)", color: "var(--amber-ink)" }}
    >
      <Info size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
      <span>
        <strong className="font-semibold">
          Investigation {position} of {ordered.length} on complaint{" "}
          <span className="mono">{capa.complaint_id}</span>.
        </strong>{" "}
        Not a duplicate: the same complaint was investigated more than once and each
        approval opens its own CAPA. This one came from{" "}
        <span className="mono">{capa.investigation_id || "an earlier run"}</span>
        {capa.opened ? <> on <span className="mono">{capa.opened}</span></> : null}.{" "}
        {siblings.length === 1 ? "The other is " : "The others are "}
        {siblings.map((s, i) => (
          <span key={s.id}>
            {i > 0 && ", "}
            <Link
              to={`/capa?highlight=${encodeURIComponent(s.id)}`}
              className="mono underline font-semibold"
            >
              {s.id}
            </Link>
            {s.opened ? ` (${s.opened})` : ""}
          </span>
        ))}
        .
      </span>
    </p>
  );
}

/** One CAPA, as a dense card: what was raised, on what evidence, whether it actually
 * worked. `?highlight=CAPA-xxxx` (set by the Done screen after an approval, and by
 * Complaints'/Memory's cross-links) scrolls to and rings the matching card so a
 * freshly-created record is unmistakable, not just "somewhere in this list". */
function CapaCard({
  capa,
  highlighted,
  siblings,
}: {
  capa: CapaRecord;
  highlighted: boolean;
  siblings: CapaRecord[];
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [highlighted]);

  return (
    <article
      ref={ref}
      className="card p-3 flex flex-col gap-2"
      style={highlighted ? { borderColor: "var(--green)", boxShadow: "0 0 0 2px var(--green)" } : undefined}
    >
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="mono font-semibold text-sm">{capa.id}</span>
          <span className="text-xs rounded-full px-2 py-0.5" style={{ background: "var(--surface-sunken)" }}>
            {capa.status}
          </span>
          {capa.defect_type && <span className="text-xs opacity-60">{humanize(capa.defect_type)}</span>}
        </div>
        {capa.effectiveness && <CapaVerdictPill verdict={capa.effectiveness.verdict} />}
      </div>

      <p className="text-sm">{capa.root_cause || capa.summary}</p>

      <SameComplaintNote capa={capa} siblings={siblings} />

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1.5 text-sm pt-1.5 border-t" style={{ borderColor: "var(--line)" }}>
        {capa.lot_id && (
          <div>
            <dt className="stat-label">Lot</dt>
            <dd className="mono">
              <Link to={`/plant?highlight=${encodeURIComponent(capa.lot_id)}`} className="underline" style={{ color: "var(--green)" }}>
                {capa.lot_id}
              </Link>
            </dd>
          </div>
        )}
        {capa.line && (
          <div>
            <dt className="stat-label">Line</dt>
            <dd className="mono">{capa.line}</dd>
          </div>
        )}
        <div>
          <dt className="stat-label">Opened</dt>
          <dd className="mono">{capa.opened || "—"}</dd>
        </div>
        {capa.complaint_id && (
          <div>
            <dt className="stat-label">Complaint</dt>
            <dd className="mono">{capa.complaint_id}</dd>
          </div>
        )}
      </dl>

      {capa.effectiveness && (
        <p className="text-xs opacity-75 pt-1">{capa.effectiveness.effect}</p>
      )}

      {capa.memory_id && (
        <Link
          to={`/memory?highlight=${encodeURIComponent(capa.memory_id)}`}
          className="tap-target inline-flex items-center text-xs font-semibold underline w-fit"
          style={{ color: "var(--green)" }}
        >
          View quality memory entry {capa.memory_id} →
        </Link>
      )}
    </article>
  );
}

/** Route "/capa" (third stop in the lifecycle: act on the work picked in Complaints)
 * — every corrective action, open or closed, with its effectiveness verdict where one
 * can be computed. This is the home `verify_capa_effectiveness` never had: before this
 * screen, CAPA-0098's "never_worked" verdict was visible only if a memory hit happened
 * to fire during a live investigation. */
export function Capa() {
  const [capas, setCapas] = useState<CapaRecord[] | null>(null);
  const [params] = useSearchParams();
  const highlight = params.get("highlight");

  useEffect(() => {
    listCapas().then(setCapas);
  }, []);

  if (!capas) return <p className="text-sm opacity-60">Loading CAPAs…</p>;

  const open = capas.filter((c) => c.status === "open");
  const closed = capas.filter((c) => c.status !== "open");

  return (
    <div className="flex flex-col gap-5">
      <LifecycleStrip current="CAPA" />
      <div>
        <h1 className="text-lg font-semibold">CAPA</h1>
        <p className="text-sm opacity-70">
          Corrective actions and whether they actually worked — recurrence, not CAPA
          count, is the measure of a working quality system.
        </p>
      </div>

      {capas.length === 0 ? (
        <p className="text-sm opacity-60">No CAPAs yet.</p>
      ) : (
        <>
          {open.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold mb-2 opacity-80">Open ({open.length})</h2>
              <div className="flex flex-col gap-2">
                {open.map((c) => (
                  <CapaCard
                    key={c.id}
                    capa={c}
                    highlighted={c.id === highlight}
                    siblings={siblingsOnSameComplaint(c, capas)}
                  />
                ))}
              </div>
            </section>
          )}
          <section>
            <h2 className="text-sm font-semibold mb-2 opacity-80">Closed ({closed.length})</h2>
            <div className="flex flex-col gap-2">
              {closed.map((c) => (
                <CapaCard
                  key={c.id}
                  capa={c}
                  highlighted={c.id === highlight}
                  siblings={siblingsOnSameComplaint(c, capas)}
                />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
