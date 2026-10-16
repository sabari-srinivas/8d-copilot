import type { AgentEvent } from "../api/types";

const AGENT_LABEL: Record<AgentEvent["agent"], string> = {
  intake: "Intake",
  vision: "Vision",
  investigator: "Investigator",
  evidence: "Evidence",
  writer: "Writer",
  system: "System",
};

function formatTime(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString(undefined, { hour12: false });
}

/** Every event the agents emit, in order, with who did it and when. This is the
 * full audit trail underneath the hypothesis cards — nothing here is filtered. */
export function Timeline({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm opacity-60">Waiting for the first event…</p>;
  }

  return (
    <ol className="flex flex-col gap-0">
      {events.map((e, i) => (
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
          </div>
        </li>
      ))}
    </ol>
  );
}
