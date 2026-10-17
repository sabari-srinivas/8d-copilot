import { AlertTriangle, CircleDot } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getInvestigation, resolveApiUrl } from "../api/client";
import { isInFlight, workingLabel } from "../api/capability";
import type { AgentEvent } from "../api/types";
import { useInvestigationStream } from "../api/useInvestigationStream";
import { DefectPhoto } from "../components/DefectPhoto";
import { HypothesisCard } from "../components/HypothesisCard";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { Timeline } from "../components/Timeline";

function ReconnectingBanner() {
  return (
    <div
      className="card p-2.5 flex items-center gap-2 text-sm"
      role="status"
      style={{ borderColor: "var(--amber)", background: "var(--amber-soft)" }}
    >
      <span
        className="inline-block h-2 w-2 rounded-full animate-pulse shrink-0"
        style={{ background: "var(--amber)" }}
        aria-hidden="true"
      />
      <span style={{ color: "var(--amber-ink)" }}>Reconnecting to the investigation…</span>
    </div>
  );
}

function WarningsNote({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div
      className="card p-3 flex flex-col gap-1 text-xs"
      style={{ borderColor: "var(--amber)", background: "var(--amber-soft)" }}
      role="note"
    >
      <p className="flex items-center gap-1.5 font-semibold" style={{ color: "var(--amber-ink)" }}>
        <AlertTriangle size={13} aria-hidden="true" />
        Provenance check flagged a number in the draft
      </p>
      {warnings.map((w, i) => (
        <p key={i} className="opacity-80">
          {w}
        </p>
      ))}
    </div>
  );
}

function StatusBanner({
  status,
  errorMessage,
  events,
  onReview,
  onEvidence,
}: {
  status: string;
  errorMessage: string | null;
  events: AgentEvent[];
  onReview: () => void;
  onEvidence: () => void;
}) {
  if (status === "failed") {
    return (
      <div
        className="card p-3 flex flex-col gap-1"
        style={{ borderColor: "var(--red)", background: "var(--red-soft)" }}
        role="alert"
      >
        <p className="text-sm font-semibold" style={{ color: "var(--red)" }}>
          The investigation could not finish
        </p>
        <p className="text-sm opacity-80">
          {errorMessage ?? "An unexpected error stopped the run before a verdict was reached."}
        </p>
      </div>
    );
  }
  if (status === "draft_ready" || status === "insufficient_evidence") {
    return (
      <div className="card p-3 flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm font-medium">
          {status === "draft_ready"
            ? "8D draft is ready for review."
            : "Draft needs more data before it can be reviewed."}
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={onEvidence}
            className="tap-target rounded-md px-4 text-sm font-semibold border transition-colors hover:bg-[var(--surface-hover)]"
            style={{ borderColor: "var(--line)" }}
          >
            See the evidence
          </button>
          <button
            type="button"
            onClick={onReview}
            className="tap-target rounded-md px-4 text-sm font-semibold text-[var(--pill-fg-strong)]"
            style={{ background: "var(--green)" }}
          >
            {status === "draft_ready" ? "Review 8D" : "Review"}
          </button>
        </div>
      </div>
    );
  }
  const inFlight = isInFlight(events);
  return (
    <div className="card p-3 flex items-center gap-2 text-sm" role="status" aria-live="polite">
      <CircleDot size={14} className="shrink-0 animate-pulse" style={{ color: "var(--green)" }} aria-hidden="true" />
      {inFlight ? workingLabel(inFlight) : "Investigation in progress…"}
    </div>
  );
}

/** Route "/inv/:id" — the live trace. This is the centrepiece: hypothesis cards
 * appear as the investigator tests them, and rejected / inconclusive ones stay on
 * screen exactly like supported ones. */
export function LiveInvestigation() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const stream = useInvestigationStream(id);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getInvestigation(id).then((inv) => setPhotoUrl(resolveApiUrl(inv.photo_url)));
  }, [id]);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumbs
        items={[
          { label: "Complaints", to: "/complaints" },
          { label: `Investigation ${id ?? ""}` },
        ]}
      />
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-lg font-semibold">
          Investigation <span className="mono text-base opacity-70">{id}</span>
        </h1>
      </div>

      {stream.reconnecting && <ReconnectingBanner />}

      <StatusBanner
        status={stream.status}
        errorMessage={stream.errorMessage}
        events={stream.events}
        onReview={() => navigate(`/inv/${id}/review`)}
        onEvidence={() => navigate(`/inv/${id}/evidence`)}
      />

      <WarningsNote warnings={stream.warnings} />

      <div className="grid lg:grid-cols-[2fr_1fr] gap-4 items-start">
        <div className="flex flex-col gap-3 min-w-0">
          <DefectPhoto photoUrl={photoUrl} defect={stream.defect} />

          {stream.memoryHits.map((hit) => (
            <div
              key={hit.id}
              className="card p-3 flex flex-col gap-1"
              style={{ borderColor: "var(--green)", background: "var(--green-soft)" }}
            >
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--green-ink)" }}>
                Similar past case found
              </p>
              <p className="text-sm">{hit.root_cause}</p>
              <p className="text-xs opacity-60 mono">
                {hit.defect_type} · {hit.line || "line n/a"} · {hit.capa_id || "no CAPA on file"}
              </p>
            </div>
          ))}

          <h2 className="text-sm font-semibold opacity-80 mt-1">Hypotheses</h2>
          {stream.hypotheses.length === 0 ? (
            <p className="text-sm opacity-60">Waiting for the investigator to propose hypotheses…</p>
          ) : (
            <div className="flex flex-col gap-2">
              {stream.hypotheses.map((h) => (
                <HypothesisCard
                  key={h.id}
                  hypothesis={h}
                  result={stream.results.find((r) => r.hypothesis_id === h.id)}
                />
              ))}
            </div>
          )}
        </div>

        <aside className="min-w-0">
          <h2 className="text-sm font-semibold opacity-80 mb-2">Agent trace</h2>
          <div className="card p-2.5 max-h-[70vh] overflow-y-auto" style={{ background: "var(--surface-sunken)" }}>
            <Timeline events={stream.events} done={stream.done} />
          </div>
        </aside>
      </div>
    </div>
  );
}
