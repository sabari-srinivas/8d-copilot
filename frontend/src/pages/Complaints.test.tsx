import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Complaints } from "./Complaints";

const COMPLAINTS = [
  {
    complaint_id: "C-2026-031", customer: "Hoshino Denso (fictional)", product: "ECU-PCB-7",
    lot_id: "L2611", defect: "solder_bridge", qty_affected: 14, qty_shipped: 500,
    received: "2026-10-14", eight_d_due: "2026-10-28", status: "open",
    text: "Solder bridging found.", due_in_working_days: 8, is_rejection: false,
    objection: "", original_eight_d: null,
  },
  {
    complaint_id: "C-2026-024", customer: "Araku Components (fictional)", product: "ECU-PCB-7",
    lot_id: "L2599", defect: "scratch", qty_affected: 3, qty_shipped: 400,
    received: "2026-09-10", eight_d_due: "2026-09-24", status: "closed",
    text: "Scratches.", due_in_working_days: null, is_rejection: false,
    objection: "", original_eight_d: null,
  },
];

vi.mock("../api/client", () => ({
  listComplaints: () => Promise.resolve(COMPLAINTS),
  listCapas: () => Promise.resolve([
    { id: "CAPA-0097", complaint_id: "C-2026-024" },
  ]),
}));

afterEach(cleanup);

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Complaints />
    </MemoryRouter>,
  );
}

describe("Complaints", () => {
  it("shows the open list by default, and not the past one", async () => {
    renderAt("/complaints");
    expect(await screen.findByRole("heading", { name: "Open complaints" })).toBeTruthy();
    expect(screen.getByText(/Hoshino Denso/)).toBeTruthy();
    expect(screen.queryByText(/Araku Components/)).toBeNull();
  });

  it("shows the past list on ?view=past, and not the open one", async () => {
    renderAt("/complaints?view=past");
    expect(await screen.findByRole("heading", { name: "Past investigations" })).toBeTruthy();
    expect(screen.getByText(/Araku Components/)).toBeTruthy();
    expect(screen.queryByText(/Hoshino Denso/)).toBeNull();
  });

  it("falls back to the open list for an unrecognised view", async () => {
    // A hand-typed or stale URL must land on the screen's primary job, not an error.
    renderAt("/complaints?view=nonsense");
    expect(await screen.findByRole("heading", { name: "Open complaints" })).toBeTruthy();
  });

  it("drops the '(fictional)' qualifier from customer names in both views", async () => {
    renderAt("/complaints");
    await screen.findByText("Hoshino Denso");
    expect(document.body.textContent).not.toMatch(/fictional/i);

    cleanup();
    renderAt("/complaints?view=past");
    await screen.findByText("Araku Components");
    expect(document.body.textContent).not.toMatch(/fictional/i);
  });

  it("keeps the KPI strip with the open list only", async () => {
    renderAt("/complaints");
    // "Soonest 8D due" is a property of open work; it is meaningless over closed rows.
    expect(await screen.findByText("Soonest 8D due")).toBeTruthy();

    cleanup();
    renderAt("/complaints?view=past");
    await screen.findByRole("heading", { name: "Past investigations" });
    expect(screen.queryByText("Soonest 8D due")).toBeNull();
  });

  it("still links a past investigation forward to the CAPA it raised", async () => {
    renderAt("/complaints?view=past");
    const link = await screen.findByRole("link", { name: /CAPA-0097/ });
    expect(link.getAttribute("href")).toBe("/capa?highlight=CAPA-0097");
  });
});
