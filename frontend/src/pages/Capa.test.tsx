import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CapaRecord } from "../api/types";
import { Capa } from "./Capa";

const CAPAS: CapaRecord[] = [
  {
    id: "CAPA-0098", investigation_id: "inv_hist_0024", complaint_id: "C-2026-024",
    lot_id: "L2389", root_cause: "Paste past its working window", owner: "Quality Manager",
    opened: "2026-07-10", status: "closed", summary: "Paste-age control procedure.",
    approver: "Priya R.", note: "", defect_type: "tombstoning", line: "L1", memory_id: "MEM-0098",
    effectiveness: {
      capa_id: "CAPA-0098", defect_type: "tombstoning", line: "L1", implemented_on: "2026-07-10",
      verdict: "never_worked", test: "Welch t-test", p_value: 0.4816,
      effect: "never actually fixed", effect_value: -0.0019, effect_unit: "defect rate",
      n_before: 10, n_immediate: 7, n_recent: 7, group_labels: [],
      before_rate: 0.02, immediate_rate: 0.0182, recent_rate: 0.014,
      p_immediate: 0.4816, p_recent: 0.0545, chart_url: null,
    },
  },
  {
    id: "CAPA-0142", investigation_id: "inv_1", complaint_id: "C-2026-031", lot_id: "L2611",
    root_cause: "Reflow peak temperature drift", owner: "Quality Manager", opened: "2026-10-16",
    status: "open", summary: "Re-qualify the Line 2 reflow profile.", approver: "Priya R.",
    note: "", defect_type: "solder_bridge", line: "L2", memory_id: "MEM-0021", effectiveness: null,
  },
];

vi.mock("../api/client", () => ({
  listCapas: () => Promise.resolve(CAPAS),
}));

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

function renderCapa(initialEntry = "/capa") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/capa" element={<Capa />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Capa", () => {
  it("surfaces CAPA-0098's never_worked verdict (previously only visible via a live memory hit)", async () => {
    renderCapa();
    expect(await screen.findByText("Never worked")).toBeTruthy();
    expect(screen.getByText("CAPA-0098")).toBeTruthy();
  });

  it("splits open and closed CAPAs into their own sections", async () => {
    renderCapa();
    await screen.findByText("Never worked");
    expect(screen.getByText("Open (1)")).toBeTruthy();
    expect(screen.getByText("Closed (1)")).toBeTruthy();
  });

  it("links a CAPA to the quality-memory entry it produced", async () => {
    renderCapa();
    const link = await screen.findByText(/View quality memory entry MEM-0098/);
    expect(link.closest("a")?.getAttribute("href")).toBe("/memory?highlight=MEM-0098");
  });

  it("highlights the CAPA named in ?highlight=", async () => {
    renderCapa("/capa?highlight=CAPA-0142");
    await screen.findByText("CAPA-0142");
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });
});
