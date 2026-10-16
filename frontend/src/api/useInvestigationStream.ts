import { useEffect, useRef, useState } from "react";
// @contract alias -> docs/contract (outside the Vite root; see vite.config.ts). Fixed
// fixture, validated against the real Pydantic models by a backend test — never edit it.
import mockEventsJson from "@contract/mock_events.json";
import { USE_MOCKS } from "./client";
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
  done: boolean;
}

/** One hook owns the live trace: every screen that shows agent progress reads from
 * here so there is exactly one source of truth for "what happened so far". */
export function useInvestigationStream(id: string | undefined): InvestigationStreamState {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const seen = useRef(new Set<number>());

  useEffect(() => {
    if (!id) return;
    seen.current.clear();
    setEvents([]);

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
    const source = new EventSource(`${base}/api/investigations/${id}/events`);
    source.onmessage = (m) => {
      const event = JSON.parse(m.data) as AgentEvent;
      push(event);
      if (event.type === "done" || event.type === "error") source.close();
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [id]);

  const by = <T,>(type: AgentEvent["type"]): T[] =>
    events.filter((e) => e.type === type).map((e) => e.data as unknown as T);

  // The vision agent's single tool_result carries the Defect itself as `data`
  // (unlike the generic {tool, summary} shape other tool_result events use).
  const defectEvent = events.find((e) => e.agent === "vision" && e.type === "tool_result");
  const defect = (defectEvent?.data as unknown as Defect | undefined) ?? null;

  const results = by<HypothesisResult>("hypothesis_result");
  const errorEvent = events.find((e) => e.type === "error");
  const draftEvent = events.find((e) => e.type === "draft_ready");

  // `failed`: the contract stream ends error -> done on a crashed run. `draft_ready`
  // and `insufficient_evidence` both arrive on the draft_ready event's own data.status.
  // Otherwise the investigation is still `running`.
  const status: Status = errorEvent
    ? "failed"
    : ((draftEvent?.data as { status?: Status } | undefined)?.status ?? "running");

  return {
    events,
    defect,
    results,
    hypotheses: by<Hypothesis>("hypothesis"),
    citations: by<Citation>("citation"),
    memoryHits: by<MemoryEntry>("memory_hit"),
    chartUrl: results.find((r) => r.chart_url)?.chart_url ?? null,
    status,
    errorMessage: (errorEvent?.data as { message?: string } | undefined)?.message
      ?? errorEvent?.detail
      ?? null,
    done: events.some((e) => e.type === "done"),
  };
}
