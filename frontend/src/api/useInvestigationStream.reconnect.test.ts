import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentEvent } from "./types";

// This suite exercises the live (non-mock) SSE path, so USE_MOCKS is forced off
// regardless of the real .env's VITE_USE_MOCKS=true.
vi.mock("./client", () => ({ USE_MOCKS: false }));

/** Minimal stand-in for the browser's EventSource, just enough surface for the hook:
 * readyState, close(), and the three handler properties it assigns. Real EventSource
 * auto-retries a transient drop on its own (readyState goes to CONNECTING, not
 * CLOSED) and fires onopen on success; the real backend replays full event history to
 * every new subscription (backend/agent/events.py EventBus.subscribe), which is what
 * the "replayed, already-seen event" step below simulates. */
class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  readyState = FakeEventSource.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  readonly close = vi.fn(() => {
    this.readyState = FakeEventSource.CLOSED;
  });

  readonly url: string;

  constructor(url: string) {
    this.url = url;
    instances.push(this);
  }
}

let instances: FakeEventSource[] = [];

function send(source: FakeEventSource, event: AgentEvent) {
  source.onmessage?.({ data: JSON.stringify(event) } as MessageEvent);
}

beforeEach(() => {
  instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useInvestigationStream reconnect (live SSE path)", () => {
  it("survives a transient drop without closing the stream, recovers, and never duplicates events", async () => {
    const { useInvestigationStream } = await import("./useInvestigationStream");
    const { result, unmount } = renderHook(() => useInvestigationStream("inv_1"));

    const source = instances[0];
    expect(source).toBeDefined();

    const event0: AgentEvent = {
      seq: 0, ts: "t0", agent: "system", type: "step_started",
      title: "Investigation started", detail: "", data: {},
    };
    const event1: AgentEvent = {
      seq: 1, ts: "t1", agent: "intake", type: "tool_result",
      title: "Complaint read", detail: "", data: {},
    };

    act(() => send(source, event0));
    expect(result.current.events.map((e) => e.seq)).toEqual([0]);
    expect(result.current.reconnecting).toBe(false);

    // The drop: the browser's own EventSource is still retrying on its own, so
    // readyState is CONNECTING, never CLOSED, while this is in flight.
    act(() => {
      source.readyState = FakeEventSource.CONNECTING;
      source.onerror?.();
    });
    expect(result.current.reconnecting).toBe(true);
    // The fix under test: a drop the browser is still retrying must never be closed
    // client-side — that would cancel the retry the hook is relying on.
    expect(source.close).not.toHaveBeenCalled();

    // Recovery: browser reconnects, backend replays full history (event0 again) plus
    // what happened since (event1).
    act(() => {
      source.readyState = FakeEventSource.OPEN;
      source.onopen?.();
      send(source, event0);
      send(source, event1);
    });
    expect(result.current.reconnecting).toBe(false);
    expect(result.current.events.map((e) => e.seq)).toEqual([0, 1]); // no duplicate of seq 0

    // The terminal event is still the deliberate way to end the stream.
    act(() => send(source, {
      seq: 2, ts: "t2", agent: "system", type: "done", title: "Investigation complete", detail: "", data: {},
    }));
    expect(source.close).toHaveBeenCalledTimes(1);

    unmount();
  });

  it("does not loop forever retrying a connection the browser itself has permanently closed", async () => {
    const { useInvestigationStream } = await import("./useInvestigationStream");
    const { result, unmount } = renderHook(() => useInvestigationStream("inv_2"));
    const source = instances[0];

    act(() => {
      source.readyState = FakeEventSource.CLOSED;
      source.onerror?.();
    });
    // Still surfaced as "reconnecting" to the user (never a silent frozen spinner),
    // even though in this case recovery won't actually happen without a page reload.
    expect(result.current.reconnecting).toBe(true);

    unmount();
  });
});
