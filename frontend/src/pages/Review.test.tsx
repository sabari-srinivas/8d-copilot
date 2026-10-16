import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EightD, Investigation } from "../api/types";
import { Review } from "./Review";

// Task 14 review: threading the backend's apply_approval (STATE_BACKEND=firestore)
// reopened a duplicate-CAPA race under genuine concurrency, closed server-side with a
// per-investigation lock (agent/agents/actions.py). This is the client-side half: an
// impatient double-click during a demo is the most likely real-world trigger for two
// concurrent /approve requests, so the Approve button must refuse to issue a second
// request while the first is still in flight — not just rely on the server guard.
const approveMock = vi.fn();

vi.mock("../api/client", () => ({
  getInvestigationReady: vi.fn(),
  approve: (...args: unknown[]) => approveMock(...args),
}));

vi.mock("../api/useInvestigationStream", () => ({
  useInvestigationStream: () => ({ status: "draft_ready" }),
}));

import { getInvestigationReady } from "../api/client";

function section(text: string) {
  return { text, citations: [] };
}

function draftInvestigation(): Investigation {
  const d = section("Section text.");
  const eight_d: EightD = { D1: d, D2: d, D3: d, D4: d, D5: d, D6: d, D7: d, D8: d };
  return {
    id: "inv_1",
    status: "draft_ready",
    complaint_id: "C-2026-031",
    lot_id: "L2611",
    created: "2026-10-16T00:00:00Z",
    photo_url: "",
    defect: null,
    hypotheses: [],
    results: [],
    citations: [],
    traveler_rows: [],
    hold_lots: [],
    eight_d,
    proposed_actions: [],
    memory_hits: [],
    missing_data: [],
    approver: "",
    chart_url: null,
  };
}

function renderReview() {
  render(
    <MemoryRouter initialEntries={["/inv/inv_1/review"]}>
      <Routes>
        <Route path="/inv/:id/review" element={<Review />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Review — Approve button double-click guard", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("issues exactly one approve request when clicked twice before the first resolves", async () => {
    vi.mocked(getInvestigationReady).mockResolvedValue(draftInvestigation());
    approveMock.mockImplementation(() => new Promise(() => {})); // never resolves in this test

    renderReview();

    const button = await screen.findByRole("button", { name: /approve 8d/i });
    // Both clicks dispatched inside ONE `act()` call, deliberately — this is what
    // actually reproduces the race a real impatient double-click can hit: two click
    // events arriving before React commits the re-render that disables the button.
    // Two separate `fireEvent.click()` calls each get their own implicit `act()` flush
    // and so would NOT reproduce it (the first call's state update commits — and
    // disables the real DOM button — before the second dispatch), which would make
    // the test pass regardless of whether `onApprove`'s own synchronous guard exists.
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });

    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(true));
    expect(approveMock).toHaveBeenCalledTimes(1);
  });

  it("allows a fresh approval attempt after a failed one", async () => {
    vi.mocked(getInvestigationReady).mockResolvedValue(draftInvestigation());
    approveMock.mockRejectedValueOnce(new Error("500 Internal Server Error"));

    renderReview();

    const button = await screen.findByRole("button", { name: /approve 8d/i });
    fireEvent.click(button);

    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    expect(approveMock).toHaveBeenCalledTimes(1);

    approveMock.mockImplementation(() => new Promise(() => {}));
    fireEvent.click(button);
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(true));
    expect(approveMock).toHaveBeenCalledTimes(2);
  });
});
