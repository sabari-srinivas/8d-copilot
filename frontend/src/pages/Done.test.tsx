import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ApproveResult, EightD, Investigation } from "../api/types";
import { Done } from "./Done";

function section(text: string) {
  return { text, citations: [] };
}

function investigation(): Investigation {
  const d = section("Section text.");
  const eight_d: EightD = { D1: d, D2: d, D3: d, D4: d, D5: d, D6: d, D7: d, D8: d };
  return {
    id: "inv_1", status: "approved", complaint_id: "C-2026-031", lot_id: "L2611",
    created: "2026-10-16T00:00:00Z", photo_url: "", defect: null, hypotheses: [],
    results: [], citations: [], traveler_rows: [], voice_note: null, hold_lots: [],
    eight_d, proposed_actions: [], memory_hits: [], missing_data: [], approver: "Priya R.",
    chart_url: null,
  };
}

vi.mock("../api/client", () => ({
  getInvestigation: () => Promise.resolve(investigation()),
}));

afterEach(() => {
  cleanup();
});

function renderDone(result: ApproveResult) {
  render(
    <MemoryRouter
      initialEntries={[{ pathname: "/inv/inv_1/done", state: { result, note: "" } }]}
    >
      <Routes>
        <Route path="/inv/:id/done" element={<Done />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Done -> CAPA handoff (no dead end after approval)", () => {
  it("offers a prominent link straight to the CAPA just created, pre-highlighted", async () => {
    renderDone({
      capa_id: "CAPA-0142", hold_id: "H-77", work_order_id: "WO-412",
      memory_id: "MEM-0021", replies: null, rejected_action_ids: [],
    });
    const link = await screen.findByText(/Continue to CAPA CAPA-0142/);
    expect(link.closest("a")?.getAttribute("href")).toBe("/capa?highlight=CAPA-0142");
  });

  it("shows no CAPA link when the CAPA action was excluded at review", async () => {
    renderDone({
      capa_id: null, hold_id: null, work_order_id: null,
      memory_id: null, replies: null, rejected_action_ids: ["A1"],
    });
    await screen.findByText(/8D approved/);
    expect(screen.queryByText(/Continue to CAPA/)).toBeNull();
  });
});
