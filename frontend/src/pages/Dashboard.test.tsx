import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DashboardSummary } from "../api/types";
import { Dashboard } from "./Dashboard";

const SUMMARY: DashboardSummary = {
  first_pass_yield: { units: 31973, defects: 282, pct: 99.12 },
  open_eight_ds: { count: 5, soonest_due_working_days: 2 },
  capas: { open: 0, recurrence_rate: 1.0, n_evaluated: 1 },
  lots_on_hold: 0,
  charts: {
    defect_rate_by_line: {
      line1: [{ lot_id: "L2551", date: "2026-09-14", rate_pct: 0.4 }],
      line2: [{ lot_id: "L2552", date: "2026-09-14", rate_pct: 0.8 }],
      line1_avg_pct: 0.41,
      line2_avg_pct: 0.76,
      marker_date: "2026-10-08",
      marker_label: "WO-388",
    },
    defect_pareto: { solder_bridge: 188, other: 94 },
    spc_reflow_peak: { limit_c: 250.0, points: [{ lot_id: "L2551", date: "2026-09-14", value: 245.0 }] },
  },
};

vi.mock("../api/client", () => ({
  getDashboardSummary: () => Promise.resolve(SUMMARY),
}));

afterEach(() => {
  cleanup();
});

function renderDashboard() {
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  it("shows the four KPI tiles computed from the summary, never hard-coded figures silently diverging", async () => {
    renderDashboard();
    expect(await screen.findByText("99.12%")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
    expect(screen.getByText(/soonest due in 2 working days/)).toBeTruthy();
  });

  it("makes every KPI tile a link (a door) to the tab that explains it", async () => {
    renderDashboard();
    await screen.findByText("99.12%");
    const yieldTile = screen.getByText("First-pass yield").closest("a");
    expect(yieldTile?.getAttribute("href")).toBe("/plant");
    const eightDTile = screen.getByText("Open 8Ds").closest("a");
    expect(eightDTile?.getAttribute("href")).toBe("/complaints");
    const capaTile = screen.getByText("Open CAPAs").closest("a");
    expect(capaTile?.getAttribute("href")).toBe("/capa");
  });

  it("omits any operator/shift breakdown tile or chart", async () => {
    renderDashboard();
    await screen.findByText("99.12%");
    expect(screen.queryByText(/operator/i)).toBeNull();
    expect(screen.queryByText(/\bshift\b/i)).toBeNull();
  });
});
