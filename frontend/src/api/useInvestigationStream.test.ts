import { describe, expect, it } from "vitest";
import fixtureWithWarning from "./__fixtures__/events_with_provenance_warning.json";
import type { AgentEvent } from "./types";
import { deriveStreamStatus } from "./useInvestigationStream";

const WARNING_FIXTURE = fixtureWithWarning as AgentEvent[];

function errorEvent(seq: number, message = "boom"): AgentEvent {
  return {
    seq,
    ts: "2026-10-16T10:00:00.000Z",
    agent: "system",
    type: "error",
    title: "The investigation could not finish",
    detail: message,
    data: { message },
  };
}

function draftReadyEvent(seq: number, status: "draft_ready" | "insufficient_evidence" = "draft_ready"): AgentEvent {
  return {
    seq,
    ts: "2026-10-16T10:00:01.000Z",
    agent: "writer",
    type: "draft_ready",
    title: "8D draft ready for review",
    detail: "",
    data: { status },
  };
}

function doneEvent(seq: number): AgentEvent {
  return { seq, ts: "2026-10-16T10:00:02.000Z", agent: "system", type: "done", title: "Investigation complete", detail: "", data: {} };
}

describe("deriveStreamStatus", () => {
  // Regression test for the review finding: the backend's `error` event is
  // deliberately NOT terminal (backend/agent/events.py TERMINAL = ("done",)) — the
  // writer publishes a non-fatal `error` when the number-provenance check flags a
  // violation, then still publishes `draft_ready` and the run finishes normally
  // (backend/agent/agents/writer.py). A client that treats any `error` as fatal would
  // show a perfectly good, fully-cited 8D as "failed" and never surface the Review
  // button. This fixture is the exact shape writer.py emits: error (seq 3) followed
  // by draft_ready (seq 4) followed by done (seq 5).
  it("yields draft_ready, not failed, when a non-fatal error is followed by draft_ready", () => {
    const result = deriveStreamStatus(WARNING_FIXTURE);
    expect(result.status).toBe("draft_ready");
    expect(result.errorMessage).toBeNull();
    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].seq).toBe(3);
  });

  it("surfaces the non-fatal error's message as a warning, not as the terminal error", () => {
    const result = deriveStreamStatus(WARNING_FIXTURE);
    expect(result.warnings[0].data).toMatchObject({
      message: "D4 cites 9.1 °C which is not in any test result or grounded fact",
    });
  });

  it("yields failed when an error has no later draft_ready (the crash backstop: error -> done)", () => {
    const events = [errorEvent(0, "boom"), doneEvent(1)];
    const result = deriveStreamStatus(events);
    expect(result.status).toBe("failed");
    expect(result.errorMessage).toBe("boom");
    expect(result.warnings).toHaveLength(0);
  });

  it("yields running when neither an error nor a draft_ready has arrived yet", () => {
    const events: AgentEvent[] = [
      { seq: 0, ts: "2026-10-16T10:00:00.000Z", agent: "intake", type: "step_started", title: "Reading complaint", detail: "", data: {} },
    ];
    const result = deriveStreamStatus(events);
    expect(result.status).toBe("running");
    expect(result.errorMessage).toBeNull();
    expect(result.warnings).toHaveLength(0);
  });

  it("does not depend on array order, only on seq — a reordered array yields the same result", () => {
    const inOrder = [errorEvent(3), draftReadyEvent(4), doneEvent(5)];
    const reversed = [doneEvent(5), draftReadyEvent(4), errorEvent(3)];
    expect(deriveStreamStatus(reversed)).toEqual(deriveStreamStatus(inOrder));
    expect(deriveStreamStatus(inOrder).status).toBe("draft_ready");
  });

  it("treats a later error (after draft_ready) as fatal, overriding the earlier draft_ready", () => {
    // Not a shape the current backend emits, but the derivation must not assume it
    // never will: "latest by seq" must mean latest, in either direction.
    const events = [draftReadyEvent(2), errorEvent(3, "late failure")];
    const result = deriveStreamStatus(events);
    expect(result.status).toBe("failed");
    expect(result.errorMessage).toBe("late failure");
  });

  it("passes through insufficient_evidence from draft_ready's own data.status untouched", () => {
    const events = [draftReadyEvent(1, "insufficient_evidence")];
    expect(deriveStreamStatus(events).status).toBe("insufficient_evidence");
  });
});
