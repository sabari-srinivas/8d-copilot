import { describeStep, isInFlight, workingLabel } from "../api/capability";
import type { AgentEvent } from "../api/types";
import { ProvenanceTag } from "./ProvenanceTag";

const AGENT_LABEL: Record<AgentEvent["agent"], string> = {
  intake: "Intake",
  vision: "Vision",
  investigator: "Investigator",
  evidence: "Evidence",
  writer: "Writer",
  reviser: "Reviser",
  system: "System",
};

function formatTime(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString(undefined, { hour12: false });
}

/** Every event the agents emit, in order, with who did it and when. This is the
 * full audit trail underneath the hypothesis cards — nothing here is filtered.
 *
 * `done`, when true, suppresses the trailing "working" row even if the last event
 * happens to be a step_started/tool_call with no further event after it — a finished
 * run must never look like it is still generating. */
export function Timeline({ events, done = false }: { events: AgentEvent[]; done?: boolean }) {
  if (events.length === 0) {
    return <p className="text-sm opacity-60">Waiting for the first event…</p>;
  }

  const inFlight = done ? null : isInFlight(events);

  return (
    <ol className="flex flex-col gap-0">
      {events.map((e, i) => {
        const capability = describeStep(e);
        return (
          <li
            key={e.seq}
            className="flex gap-3 py-2"
            style={{ borderTop: i === 0 ? "none" : "1px solid var(--line)" }}
          >
            <time className="mono text-xs opacity-60 shrink-0 w-20 pt-0.5" dateTime={e.ts}>
              {formatTime(e.ts)}
            </time>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="text-[11px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
                  style={{ background: "var(--line)" }}
                >
                  {AGENT_LABEL[e.agent]}
                </span>
                <span className="text-sm font-medium truncate">{e.title}</span>
              </div>
              {e.detail && <p className="text-xs opacity-70 mt-0.5">{e.detail}</p>}
              {capability && (
                <p className="mt-0.5">
                  <ProvenanceTag tone={capability.kind}>{capability.text}</ProvenanceTag>
                </p>
              )}
            </div>
          </li>
        );
      })}
      {inFlight && (
        <li
          className="flex gap-3 py-2"
          style={{ borderTop: "1px solid var(--line)" }}
          aria-live="polite"
        >
          <span className="w-20 shrink-0" aria-hidden="true" />
          <div className="min-w-0 flex-1 flex items-center gap-2">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full animate-pulse shrink-0"
              style={{ background: "var(--green)" }}
              aria-hidden="true"
            />
            <span className="text-sm opacity-80">{workingLabel(inFlight)}</span>
          </div>
        </li>
      )}
    </ol>
  );
}
