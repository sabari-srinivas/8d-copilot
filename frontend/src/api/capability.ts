import type { AgentEvent } from "./types";

/** Which half of the product's division of labour a piece of the trace belongs to —
 * the same three buckets CHANGE_REQUESTS.md #2 draws for the rest of the UI:
 * "ai" = a Gemini/embedding call proposed this, "computed" = deterministic code (stats,
 * plant-data lookups) decided or fetched this, "quoted" = text lifted verbatim from a
 * source document. Never a fourth bucket — every event either names a real capability
 * or gets no tag at all (see describeStep). */
export type Provenance = "ai" | "computed" | "quoted";

export interface StepDescription {
  /** A short, judge-legible phrase naming the capability in flight — never a colour,
   * always read-aloud-able on its own. */
  text: string;
  kind: Provenance;
}

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

function asString(v: unknown): string {
  return typeof v === "string" ? v : "";
}

// Mirrors backend/agent/agents/evidence.py's SOURCE_LABELS — how a filename is spoken
// aloud. Kept in sync by eye (small, stable list); falls back to a capitalized stem for
// anything not listed, same as the backend does.
const SOURCE_LABELS: Record<string, string> = {
  "pfmea.md": "PFMEA",
  "control_plan.md": "Control plan",
  "past_8d_tombstoning.md": "Past 8D (tombstoning)",
  "past_8d_voids.md": "Past 8D (voids)",
};

export function prettySource(source: string): string {
  if (!source) return "the source document";
  if (SOURCE_LABELS[source]) return SOURCE_LABELS[source];
  const stem = source.replace(/\.md$/i, "").replace(/_/g, " ");
  return stem.charAt(0).toUpperCase() + stem.slice(1);
}

/**
 * Names the real Gen AI (or deliberately non-AI) capability behind one event, derived
 * only from fields the event actually carries — `agent`, `type`, `title` and `data`.
 * Returns null when an event has no capability worth narrating (e.g. the system's
 * "Investigation started"/"done" bookends) rather than inventing one.
 *
 * Deliberately permissive about exact tool names: the mock golden path
 * (docs/contract/mock_events.json) and the live agents (backend/agent/agents/*.py) use
 * slightly different tool-name spellings for the same step (e.g. "read_complaint" vs
 * "parse_complaint"), so matching leans on `agent` + `type` first and only refines with
 * `data.tool`/`title` where that distinguishes two different capabilities on the same
 * agent (e.g. intake's complaint parse, which is a Gemini call, vs its traveler parse,
 * which is plain openpyxl and must never be labelled AI).
 */
export function describeStep(event: AgentEvent): StepDescription | null {
  const data = asRecord(event.data);
  const tool = asString(data.tool);

  switch (event.agent) {
    case "vision":
      return { text: "Gemini multimodal vision", kind: "ai" };

    case "intake":
      if (tool.includes("traveler")) {
        return { text: "Spreadsheet parsed deterministically, not AI", kind: "computed" };
      }
      return { text: "Structured output, schema-validated", kind: "ai" };

    case "investigator": {
      if (event.type === "memory_hit") {
        return { text: "Vector similarity match over past confirmed causes", kind: "ai" };
      }
      if (tool === "search_quality_memory" || /quality memory/i.test(event.title)) {
        return { text: "Vector similarity search over past confirmed causes", kind: "ai" };
      }
      if (event.type === "hypothesis") {
        return { text: "Agentic hypothesis generation across the 6Ms, Gemini", kind: "ai" };
      }
      if (event.type === "hypothesis_result") {
        const nDefect = typeof data.n_defect === "number" ? data.n_defect : undefined;
        const nGood = typeof data.n_good === "number" ? data.n_good : undefined;
        const test = asString(data.test) || "statistical test";
        const n = nDefect != null && nGood != null ? nDefect + nGood : undefined;
        return {
          text: `${test}, scipy${n != null ? ` · ${n} lots (${nDefect} defect, ${nGood} good)` : ""}`,
          kind: "computed",
        };
      }
      if (tool === "test_hypothesis" || /^Testing:/.test(event.title)) {
        return { text: "Statistical test queued — scipy decides this, not the model", kind: "computed" };
      }
      if (["get_lot_genealogy", "get_maintenance_events", "get_process_window"].includes(tool)) {
        return { text: "Plant data lookup, not AI", kind: "computed" };
      }
      return null;
    }

    case "evidence": {
      if (event.type === "citation") {
        return { text: `Quoted from ${prettySource(asString(data.source))}`, kind: "quoted" };
      }
      if (tool === "search_quality_docs") {
        const args = asRecord(data.args);
        const k = typeof args.k === "number" ? args.k : undefined;
        return {
          text: `Embedding search, vector similarity${k ? ` — top ${k} passages per query` : ""}`,
          kind: "ai",
        };
      }
      if (event.type === "tool_result") {
        const labels = Array.isArray(data.labels) ? data.labels.length : undefined;
        return {
          text: `Embedding search${labels != null ? ` — ${labels} citations retrieved` : ""}`,
          kind: "ai",
        };
      }
      return { text: "Embedding search over the PFMEA and control plan", kind: "ai" };
    }

    case "writer":
      if (event.type === "draft_ready") {
        return { text: "Every number checked against a tool result", kind: "computed" };
      }
      return { text: "Grounded generation, Gemini", kind: "ai" };

    default:
      return null;
  }
}

/** The event currently in flight — the last event in the stream, if (and only if) it is
 * a step that has started but has not yet published its result. Used to light up a
 * "working" state during the silent gap between events (CHANGE_REQUESTS.md #4/#9):
 * vision alone has been observed taking up to 22s with nothing on screen. */
export function isInFlight(events: AgentEvent[]): AgentEvent | null {
  if (events.length === 0) return null;
  const last = events[events.length - 1];
  return last.type === "step_started" || last.type === "tool_call" ? last : null;
}

/** The in-flight banner's text. Says "AI is generating" only when the capability
 * actually in flight is a model/embedding call — a deterministic plant-data lookup or
 * spreadsheet parse gets "Running", never "AI is generating", for the same reason the
 * verdict pills never say "AI": this product's whole claim is that not everything here
 * is the model. */
export function workingLabel(event: AgentEvent): string {
  const step = describeStep(event);
  if (!step) return `Working — ${event.title}…`;
  const verb = step.kind === "computed" ? "Running" : "AI is generating";
  return `${verb} — ${step.text}…`;
}
