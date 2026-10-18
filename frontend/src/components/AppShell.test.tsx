import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";

/** Two open and one closed, each carrying the "(fictional)" qualifier the real data
 * carries — the sidebar must neither list them individually (CR #17) nor print the
 * qualifier. An empty list would have let both regressions through. */
const COMPLAINTS = [
  { complaint_id: "C-2026-031", customer: "Hoshino Denso (fictional)", status: "open" },
  { complaint_id: "C-2026-034", customer: "Meridian Auto Electronics (fictional)", status: "open" },
  { complaint_id: "C-2026-024", customer: "Araku Components (fictional)", status: "closed" },
];

const prefetchAll = vi.fn();

vi.mock("../api/client", () => ({
  getHealth: () => Promise.resolve({ ok: true, model: "", replay: null, backends: {} }),
  listComplaints: () => Promise.resolve(COMPLAINTS),
  listCapas: () => Promise.resolve([]),
  prefetchAll: () => prefetchAll(),
}));

// This jsdom environment's own window.localStorage is a non-functional stub (no
// getItem/setItem/clear at all -- a quirk of this jsdom/vitest version, not of the
// app). Stub a real in-memory Storage so the collapse-persistence test actually
// exercises AppShell's try/getItem/setItem logic instead of silently no-op'ing.
function fakeStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (k) => store.get(k) ?? null,
    setItem: (k, v) => { store.set(k, String(v)); },
    removeItem: (k) => { store.delete(k); },
    clear: () => store.clear(),
    key: (i) => Array.from(store.keys())[i] ?? null,
    get length() { return store.size; },
  };
}

beforeEach(() => {
  vi.stubGlobal("localStorage", fakeStorage());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderShell() {
  return render(
    <MemoryRouter>
      <AppShell>
        <p>content</p>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("shows exactly the five lifecycle tabs, in order", () => {
    renderShell();
    const nav = screen.getAllByRole("navigation", { name: "Primary" })[0];
    const labels = ["Dashboard", "Complaints", "CAPA", "Memory", "Plant"];
    for (const label of labels) {
      expect(nav.textContent).toContain(label);
    }
  });

  it("names the plant without the '(fictional)' qualifier", async () => {
    renderShell();
    expect(await screen.findByText("Sree Electronics, Chennai")).toBeTruthy();
    expect(screen.queryByText(/fictional/i)).toBeNull();
  });

  it("opens the complaints dropdown to two views, not to every complaint", async () => {
    renderShell();

    // The dropdown is a navigation control; listing each complaint made it a second
    // copy of the page it navigates to (CR #17).
    expect(await screen.findByRole("link", { name: /Open complaints/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Past investigations/ })).toBeTruthy();
    for (const c of COMPLAINTS) {
      expect(screen.queryByText(c.complaint_id)).toBeNull();
    }
    expect(screen.queryByText(/Hoshino Denso/)).toBeNull();
  });

  it("points each view at the route the main section branches on", async () => {
    renderShell();
    const open = await screen.findByRole("link", { name: /Open complaints/ });
    const past = screen.getByRole("link", { name: /Past investigations/ });
    expect(open.getAttribute("href")).toBe("/complaints");
    expect(past.getAttribute("href")).toBe("/complaints?view=past");
  });

  it("counts each view beside its label, so the numbers survive the collapse", async () => {
    renderShell();
    const open = await screen.findByRole("link", { name: /Open complaints/ });
    const past = screen.getByRole("link", { name: /Past investigations/ });
    expect(open.textContent).toContain("2");
    expect(past.textContent).toContain("1");
  });

  it("carries no '(fictional)' qualifier anywhere in the shell", async () => {
    renderShell();
    await screen.findByRole("link", { name: /Open complaints/ });
    const shell = screen.getAllByRole("navigation", { name: "Primary" })[0];
    expect(shell.textContent).not.toMatch(/fictional/i);
    expect(document.body.textContent).not.toMatch(/fictional/i);
  });

  it("warms every tab's data once as soon as the shell mounts", () => {
    prefetchAll.mockClear();
    renderShell();
    // CR #18: each tab fetches on mount, so without this the first visit to each one
    // pays the full round trip in front of the user.
    expect(prefetchAll).toHaveBeenCalledTimes(1);
  });

  it("moves the persona out of the header to the bottom of the sidebar", () => {
    renderShell();
    expect(screen.getByText("Priya R.")).toBeTruthy();
    expect(screen.getByText("Quality Engineer")).toBeTruthy();
  });

  it("carries no demo-data wording anywhere in the shell", () => {
    renderShell();
    expect(screen.queryByText(/Synthetic demo data/)).toBeNull();
    expect(screen.queryByText(/Built with Gemini/)).toBeNull();
    expect(screen.queryByText(/demo data/i)).toBeNull();
  });

  it("collapses the sidebar and persists the state across remounts (navigation)", () => {
    const { unmount } = renderShell();
    const toggle = screen.getByRole("button", { name: /collapse sidebar/i });
    fireEvent.click(toggle);
    expect(localStorage.getItem("sidebar_collapsed")).toBe("true");
    unmount();

    renderShell();
    expect(screen.getByRole("button", { name: /expand sidebar/i })).toBeTruthy();
  });
});
