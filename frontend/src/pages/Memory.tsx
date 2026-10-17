import { useEffect, useState } from "react";
import { listMemory } from "../api/client";
import type { MemoryEntry } from "../api/types";

/** Route "/memory" — every confirmed cause the system has saved, so the next
 * investigator can see whether this defect has happened before. */
export function Memory() {
  const [entries, setEntries] = useState<MemoryEntry[] | null>(null);

  useEffect(() => {
    listMemory().then(setEntries);
  }, []);

  if (!entries) return <p className="text-sm opacity-60">Loading quality memory…</p>;

  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-lg font-semibold">Quality memory</h1>
      <p className="text-sm opacity-70">
        Confirmed root causes from past investigations, saved so the next similar
        defect gets caught faster.
      </p>

      {entries.length === 0 ? (
        <p className="text-sm opacity-60">Nothing saved yet.</p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {entries.map((m) => (
            <article key={m.id} className="card card-interactive p-3 flex flex-col gap-1.5">
              <span className="stat-label" style={{ color: "var(--green-ink)" }}>
                {m.defect_type.replace(/_/g, " ")}
              </span>
              <p className="text-sm">{m.root_cause}</p>
              <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-sm pt-1.5 border-t" style={{ borderColor: "var(--line)" }}>
                {m.parameter && (
                  <div>
                    <dt className="stat-label">Parameter</dt>
                    <dd className="mono">{m.parameter}</dd>
                  </div>
                )}
                {m.line && (
                  <div>
                    <dt className="stat-label">Line</dt>
                    <dd className="mono">{m.line}</dd>
                  </div>
                )}
                {m.capa_id && (
                  <div>
                    <dt className="stat-label">CAPA</dt>
                    <dd className="mono">{m.capa_id}</dd>
                  </div>
                )}
                {m.lot_id && (
                  <div>
                    <dt className="stat-label">Lot</dt>
                    <dd className="mono">{m.lot_id}</dd>
                  </div>
                )}
              </dl>
              {m.created && <p className="mono text-xs opacity-50 mt-1">{m.created}</p>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
