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

// Dot colour on the trace rail — reinforces the ai/computed/quoted split the rest of
// the trace already states in words (ProvenanceTag), never the only signal.
const DOT_COLOR: Record<"ai" | "computed" | "quoted" | "neutral", string> = {
  ai: "var(--ink)",
  computed: "var(--green)",
  quoted: "var(--grey)",
  neutral: "var(--line-strong)",
};

/** Every event the agents emit, in order, with who did it and when. This is the
 * full audit trail underneath the hypothesis cards — nothing here is filtered.
 * Styled as a readout (mono timestamps, a connecting rail, compact rows) rather than
 * chat bubbles — this is instrumentation, not a conversation.
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
        const dot = DOT_COLOR[capability?.kind ?? "neutral"];
        return (
          <li key={e.seq} className="flex gap-2.5 py-1.5">
            <time className="mono text-[11px] opacity-55 shrink-0 w-14 pt-0.5 text-right" dateTime={e.ts}>
              {formatTime(e.ts)}
            </time>
            <div className="shrink-0 flex flex-col items-center" aria-hidden="true">
              <span className="h-1.5 w-1.5 rounded-full shrink-0 mt-1.5" style={{ background: dot }} />
              {i < events.length - 1 && <span className="w-px flex-1 mt-0.5" style={{ background: "var(--line)" }} />}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="mono text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
                  style={{ background: "var(--card)" }}
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
        <li className="flex gap-2.5 py-1.5" aria-live="polite">
          <span className="w-14 shrink-0" aria-hidden="true" />
          <div className="shrink-0 flex items-center" aria-hidden="true">
            <span className="h-1.5 w-1.5 rounded-full animate-pulse shrink-0" style={{ background: "var(--green)" }} />
          </div>
          <div className="min-w-0 flex-1 flex items-center">
            <span className="text-sm opacity-80">{workingLabel(inFlight)}</span>
          </div>
        </li>
      )}
    </ol>
  );
}
