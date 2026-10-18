import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { listCapas } from "../api/client";
import type { CapaRecord } from "../api/types";
import { Capa, siblingsOnSameComplaint } from "./Capa";

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
  listCapas: vi.fn(() => Promise.resolve(CAPAS)),
}));

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(listCapas).mockResolvedValue(CAPAS);
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

describe("two CAPAs on one complaint (CR #19)", () => {
  /** The live pair: C-2026-033 / L2612 investigated on two days, each approval opening
   * its own CAPA. Near-identical apart from the date, which is exactly what made them
   * read as duplicates. */
  const base = CAPAS[1];
  const PAIR: CapaRecord[] = [
    { ...base, id: "CAPA-0142", investigation_id: "inv_8de98e06", complaint_id: "C-2026-033",
      lot_id: "L2612", opened: "2026-10-18", memory_id: "MEM-0001" },
    { ...base, id: "CAPA-0143", investigation_id: "inv_66882e7e", complaint_id: "C-2026-033",
      lot_id: "L2612", opened: "2026-10-17", memory_id: "MEM-0002" },
  ];

  it("pairs CAPAs that share a complaint, oldest first", () => {
    expect(siblingsOnSameComplaint(PAIR[0], PAIR).map((c) => c.id)).toEqual(["CAPA-0143"]);
    expect(siblingsOnSameComplaint(PAIR[1], PAIR).map((c) => c.id)).toEqual(["CAPA-0142"]);
  });

  it("says nothing when each complaint has one CAPA", () => {
    // The note must disappear by itself once the records are clean -- it describes the
    // data, it is not a fixed caption.
    expect(siblingsOnSameComplaint(CAPAS[0], CAPAS)).toEqual([]);
    expect(siblingsOnSameComplaint(CAPAS[1], CAPAS)).toEqual([]);
  });

  it("ignores a CAPA with no complaint rather than grouping all of them together", () => {
    const orphans = [{ ...base, id: "CAPA-A", complaint_id: "" },
                     { ...base, id: "CAPA-B", complaint_id: "" }];
    expect(siblingsOnSameComplaint(orphans[0], orphans)).toEqual([]);
  });

  it("numbers each card by date, so 1 of 2 is the earlier investigation", async () => {
    vi.mocked(listCapas).mockResolvedValue(PAIR);
    renderCapa();
    await screen.findByText(/Investigation 1 of 2/);
    expect(screen.getByText(/Investigation 2 of 2/)).toBeTruthy();
    expect(screen.getAllByText(/on complaint/)).toHaveLength(2);
  });

  it("states it is not a duplicate, and names the investigation each came from", async () => {
    vi.mocked(listCapas).mockResolvedValue(PAIR);
    renderCapa();
    await screen.findByText(/Investigation 1 of 2/);
    const notes = screen.getAllByText(/Not a duplicate/);
    expect(notes).toHaveLength(2);
    expect(screen.getByText("inv_8de98e06")).toBeTruthy();
    expect(screen.getByText("inv_66882e7e")).toBeTruthy();
  });

  it("links each note to the other CAPA", async () => {
    vi.mocked(listCapas).mockResolvedValue(PAIR);
    renderCapa();
    await screen.findByText(/Investigation 1 of 2/);
    const links = screen.getAllByRole("link", { name: /CAPA-014/ });
    const hrefs = links.map((a) => a.getAttribute("href")).sort();
    expect(hrefs).toEqual(["/capa?highlight=CAPA-0142", "/capa?highlight=CAPA-0143"]);
  });
});
