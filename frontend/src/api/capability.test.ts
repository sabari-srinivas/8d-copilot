import { describe, expect, it } from "vitest";
import mockEventsJson from "@contract/mock_events.json";
import { describeStep, isInFlight, prettySource, workingLabel } from "./capability";
import type { AgentEvent } from "./types";

const MOCK_EVENTS = mockEventsJson as AgentEvent[];

function find(agent: AgentEvent["agent"], type: AgentEvent["type"], seq?: number): AgentEvent {
  const matches = MOCK_EVENTS.filter((e) => e.agent === agent && e.type === type);
  const event = seq != null ? matches.find((e) => e.seq === seq) : matches[0];
  if (!event) throw new Error(`no ${agent}/${type} event in the golden path fixture`);
  return event;
}

describe("describeStep — golden path fixture", () => {
  it("names vision's capability as Gemini multimodal vision, tagged AI", () => {
    const step = describeStep(find("vision", "tool_result"));
    expect(step).toEqual({ text: "Gemini multimodal vision", kind: "ai" });
  });

  it("names intake's complaint parse as structured output, tagged AI", () => {
    const step = describeStep(find("intake", "tool_result", 2));
    expect(step?.kind).toBe("ai");
    expect(step?.text).toMatch(/structured output/i);
  });

  it("never tags the traveler spreadsheet parse as AI — it is plain openpyxl, not a model call", () => {
    const step = describeStep(find("intake", "tool_result", 3));
    expect(step?.kind).toBe("computed");
    expect(step?.text).toMatch(/not AI/i);
  });

  it("names the voice note's capability as Gemini multimodal audio, tagged AI (CR #12)", () => {
    const call = describeStep(find("intake", "tool_call", 4));
    expect(call).toEqual({ text: "Gemini multimodal audio — transcription + extraction", kind: "ai" });
    const result = describeStep(find("intake", "tool_result", 5));
    expect(result?.kind).toBe("ai");
    expect(result?.text).toMatch(/audio/i);
  });

  it("names the quality-memory check as vector similarity search, tagged AI", () => {
    const step = describeStep(find("investigator", "step_started"));
    expect(step?.kind).toBe("ai");
    expect(step?.text).toMatch(/vector similarity/i);
  });

  it("names a hypothesis proposal as agentic generation across the 6Ms, tagged AI", () => {
    const step = describeStep(find("investigator", "hypothesis"));
    expect(step?.kind).toBe("ai");
    expect(step?.text).toMatch(/6Ms/);
  });

  it("names a hypothesis result as computed from lot data — never AI — with the real n", () => {
    const h2 = MOCK_EVENTS.find(
      (e) => e.type === "hypothesis_result" && (e.data as { hypothesis_id?: string }).hypothesis_id === "H2",
    );
    if (!h2) throw new Error("H2 result missing from fixture");
    const step = describeStep(h2);
    expect(step?.kind).toBe("computed");
    // n_defect=6, n_good=58 in the fixture — the total must come from the event's own
    // data, never a hard-coded number.
    expect(step?.text).toContain("64 lots");
    expect(step?.text).toContain("Welch t-test");
  });

  it("names evidence's document search as embedding search, tagged AI", () => {
    // The golden path fixture only carries evidence's `citation` events (see
    // docs/contract/README.md's type table) — `step_started`/`tool_call` for this agent
    // are real shapes agent/agents/evidence.py emits but aren't in the 23-event fixture,
    // so this constructs the shape directly rather than skip the capability untested.
    const searching: AgentEvent = {
      seq: 99,
      ts: "2026-10-16T10:02:10.000Z",
      agent: "evidence",
      type: "step_started",
      title: "Looking for the PFMEA row and control plan item that cover this",
      detail: "",
      data: {},
    };
    const step = describeStep(searching);
    expect(step?.kind).toBe("ai");
    expect(step?.text).toMatch(/embedding search/i);
  });

  it("names a citation as quoted from its source document, never AI", () => {
    const step = describeStep(find("evidence", "citation"));
    expect(step?.kind).toBe("quoted");
    expect(step?.text).toMatch(/^Quoted from/);
  });

  it("names the writer's draft_ready as the provenance check, computed — not AI", () => {
    // draft_ready itself reports the number-provenance check (agent/tools/provenance.py),
    // which is deterministic Python, not the model that drafted the prose.
    const step = describeStep(find("writer", "draft_ready"));
    expect(step?.kind).toBe("computed");
    expect(step?.text).toMatch(/tool result/i);
  });

  it("names the writer's own drafting step_started as grounded generation, tagged AI", () => {
    const draftingStarted: AgentEvent = {
      seq: 99,
      ts: "2026-10-16T10:02:11.000Z",
      agent: "writer",
      type: "step_started",
      title: "Drafting the 8D",
      detail: "",
      data: {},
    };
    const step = describeStep(draftingStarted);
    expect(step?.kind).toBe("ai");
    expect(step?.text).toMatch(/gemini/i);
  });

  it("returns null for system bookends with no capability to narrate", () => {
    expect(describeStep(find("system", "step_started"))).toBeNull();
    expect(describeStep(find("system", "done"))).toBeNull();
  });
});

describe("isInFlight", () => {
  it("is null once the run has finished (last event is done)", () => {
    expect(isInFlight(MOCK_EVENTS)).toBeNull();
  });

  it("is null for an empty stream", () => {
    expect(isInFlight([])).toBeNull();
  });

  it("names the last event when it is a step_started with no result yet — the silent gap", () => {
    const prefix = MOCK_EVENTS.slice(0, 7); // ends on vision's step_started (seq 6)
    const inFlight = isInFlight(prefix);
    expect(inFlight?.seq).toBe(6);
    expect(inFlight?.agent).toBe("vision");
  });

  it("names the last event when it is a tool_call awaiting its tool_result", () => {
    const prefix = MOCK_EVENTS.slice(0, 2); // ends on intake's tool_call (seq 1)
    const inFlight = isInFlight(prefix);
    expect(inFlight?.seq).toBe(1);
  });

  it("is null once that step's result has landed", () => {
    const prefix = MOCK_EVENTS.slice(0, 8); // vision's tool_result (seq 7) has landed
    expect(isInFlight(prefix)).toBeNull();
  });
});

describe("prettySource", () => {
  it("names the known quality documents the way a person would say them aloud", () => {
    expect(prettySource("pfmea.md")).toBe("PFMEA");
    expect(prettySource("control_plan.md")).toBe("Control plan");
  });

  it("falls back to a capitalized stem for an unlisted source", () => {
    expect(prettySource("some_new_doc.md")).toBe("Some new doc");
  });

  it("names the absence of a source rather than rendering an empty label", () => {
    expect(prettySource("")).toBe("the source document");
  });
});

describe("workingLabel", () => {
  it("says AI is generating for a model call in flight (vision)", () => {
    const vision = find("vision", "step_started");
    expect(workingLabel(vision)).toBe("AI is generating — Gemini multimodal vision…");
  });

  it("says Running, never AI is generating, for a deterministic step in flight", () => {
    // Not in the 23-event golden path fixture (it has no maintenance-lookup gap long
    // enough to observe mid-flight), but a shape investigator.py genuinely emits before
    // get_lot_genealogy/get_maintenance_events return — a plant-data lookup, not a model
    // call, and must never be announced as "AI is generating".
    const plantLookup: AgentEvent = {
      seq: 99,
      ts: "2026-10-16T10:02:03.600Z",
      agent: "investigator",
      type: "tool_call",
      title: "Pulling lot genealogy and process window for L2611",
      detail: "",
      data: { tool: "get_lot_genealogy", args: { lot_id: "L2611" } },
    };
    expect(workingLabel(plantLookup)).toMatch(/^Running —/);
    expect(workingLabel(plantLookup)).not.toMatch(/AI is generating/);
  });

  it("falls back to the event's own title when it carries no named capability", () => {
    const started = find("system", "step_started");
    expect(workingLabel(started)).toBe(`Working — ${started.title}…`);
  });
});
