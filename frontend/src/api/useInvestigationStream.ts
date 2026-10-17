import { useEffect, useRef, useState } from "react";
// @contract alias -> docs/contract (outside the Vite root; see vite.config.ts). Fixed
// fixture, validated against the real Pydantic models by a backend test — never edit it.
import mockEventsJson from "@contract/mock_events.json";
import { USE_MOCKS } from "./client";
import { getDemoCode } from "./demoCode";
import type { AgentEvent, Citation, Defect, Hypothesis, HypothesisResult, MemoryEntry, Status } from "./types";

const MOCK_EVENTS = mockEventsJson as AgentEvent[];
const MOCK_TICK_MS = 600;

export interface InvestigationStreamState {
  events: AgentEvent[];
  defect: Defect | null;
  hypotheses: Hypothesis[];
  results: HypothesisResult[];
  citations: Citation[];
  memoryHits: MemoryEntry[];
  chartUrl: string | null;
  status: Status;
  errorMessage: string | null;
  /** Non-fatal `error` events that happened before a `draft_ready` still arrived —
   * e.g. a number-provenance warning the run survived. Rendered as a small advisory,
   * not swallowed: see deriveStreamStatus below. */
  warnings: string[];
  /** True while the SSE connection has dropped and the browser hasn't reconnected
   * (or recovered) yet. Only meaningful when !USE_MOCKS. */
  reconnecting: boolean;
  done: boolean;
}

/**
 * Pure and exported (no hook, no DOM) so the status/warning derivation can be unit
 * tested directly against fixtures — see useInvestigationStream.test.ts.
 *
 * `error` is deliberately NOT terminal on the backend (backend/agent/events.py's
 * `TERMINAL = ("done",)`, and backend/agent/agents/writer.py): the writer publishes a
 * non-fatal `error` when the number-provenance check flags a violation in the drafted
 * 8D, and then still publishes `draft_ready` and the run finishes normally. The only
 * genuinely fatal shape is `error` with no `draft_ready` ever following it — the crash
 * backstop in backend/agent/main.py's `_run`, which publishes `error` then `done` and
 * never `draft_ready`.
 *
 * So status is derived from whichever of "the latest draft_ready" and "the latest
 * error" has the higher sequence number — never from "does an error event exist
 * anywhere in the list" (that treats a survived warning as fatal) and never by relying
 * on array/arrival order (events can arrive or be supplied out of order; `seq` is the
 * only thing that is authoritative).
 */
export function deriveStreamStatus(events: AgentEvent[]): {
  status: Status;
  errorMessage: string | null;
  warnings: AgentEvent[];
} {
  const errorEvents = events.filter((e) => e.type === "error");
  const draftEvents = events.filter((e) => e.type === "draft_ready");
  const latestBySeq = (list: AgentEvent[]): AgentEvent | null =>
    list.reduce<AgentEvent | null>((best, e) => (!best || e.seq > best.seq ? e : best), null);
  const latestError = latestBySeq(errorEvents);
  const latestDraft = latestBySeq(draftEvents);

  const draftIsLatest = latestDraft != null && (latestError == null || latestDraft.seq > latestError.seq);

  if (draftIsLatest) {
    const data = latestDraft!.data as { status?: Status } | undefined;
    return {
      status: data?.status ?? "draft_ready",
      errorMessage: null,
      // Non-fatal: the run produced this draft anyway. Surfaced to the reviewer
      // rather than discarded — "we flagged a number that wasn't cited" is useful.
      warnings: errorEvents.filter((e) => e.seq < latestDraft!.seq),
    };
  }
  if (latestError != null) {
    const data = latestError.data as { message?: string } | undefined;
    return {
      status: "failed",
      errorMessage: data?.message ?? latestError.detail ?? null,
      warnings: [],
    };
  }
  return { status: "running", errorMessage: null, warnings: [] };
}

/** One hook owns the live trace: every screen that shows agent progress reads from
 * here so there is exactly one source of truth for "what happened so far". */
export function useInvestigationStream(id: string | undefined): InvestigationStreamState {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [reconnecting, setReconnecting] = useState(false);
  const seen = useRef(new Set<number>());

  useEffect(() => {
    if (!id) return;
    seen.current.clear();
    setEvents([]);
    setReconnecting(false);

    const push = (e: AgentEvent) => {
      if (seen.current.has(e.seq)) return; // SSE reconnect replays history
      seen.current.add(e.seq);
      setEvents((prev) => [...prev, e].sort((a, b) => a.seq - b.seq));
    };

    if (USE_MOCKS) {
      let i = 0;
      const timer = setInterval(() => {
        if (i >= MOCK_EVENTS.length) {
          clearInterval(timer);
          return;
        }
        push(MOCK_EVENTS[i++]);
      }, MOCK_TICK_MS);
      return () => clearInterval(timer);
    }

    const base = import.meta.env.VITE_API_URL ?? "";
    // EventSource can't set custom headers, so the demo code (when one is
    // configured) travels as a query param here — see main.py's require_demo_code.
    const code = getDemoCode();
    const url = `${base}/api/investigations/${id}/events${code ? `?code=${encodeURIComponent(code)}` : ""}`;
    const source = new EventSource(url);
    source.onopen = () => setReconnecting(false);
    source.onmessage = (m) => {
      const event = JSON.parse(m.data) as AgentEvent;
      push(event);
      setReconnecting(false);
      // `error` is not terminal (see deriveStreamStatus above) — only `done` ends
      // the stream, matching the backend's own TERMINAL tuple exactly.
      if (event.type === "done") source.close();
    };
    source.onerror = () => {
      // A transient drop (wifi blip, backend hot-reload, a backgrounded tab) leaves
      // the browser's own EventSource retrying on its own — readyState is CONNECTING,
      // not CLOSED — and the backend replays full history to the new subscription
      // (agent/events.py EventBus.subscribe), so the seq-based dedup in `push` above
      // means the replay never shows an event twice. Calling close() here would
      // cancel that retry for nothing and end the stream permanently on a drop that
      // would otherwise have healed itself. Only once the browser itself has given up
      // (readyState CLOSED — e.g. the server rejected the request outright) is there
      // nothing left to wait for.
      if (source.readyState === EventSource.CLOSED) {
        source.close();
      }
      setReconnecting(source.readyState !== EventSource.OPEN);
    };
    return () => source.close();
  }, [id]);

  const by = <T,>(type: AgentEvent["type"]): T[] =>
    events.filter((e) => e.type === type).map((e) => e.data as unknown as T);

  // The vision agent's single tool_result carries the Defect itself as `data`
  // (unlike the generic {tool, summary} shape other tool_result events use).
  const defectEvent = events.find((e) => e.agent === "vision" && e.type === "tool_result");
  const defect = (defectEvent?.data as unknown as Defect | undefined) ?? null;

  const results = by<HypothesisResult>("hypothesis_result");
  const { status, errorMessage, warnings } = deriveStreamStatus(events);

  return {
    events,
    defect,
    results,
    hypotheses: by<Hypothesis>("hypothesis"),
    citations: by<Citation>("citation"),
    memoryHits: by<MemoryEntry>("memory_hit"),
    chartUrl: results.find((r) => r.chart_url)?.chart_url ?? null,
    status,
    errorMessage,
    warnings: warnings.map((e) => (e.data as { message?: string } | undefined)?.message ?? e.detail ?? e.title),
    reconnecting,
    done: events.some((e) => e.type === "done"),
  };
}
