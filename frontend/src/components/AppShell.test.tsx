import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";

vi.mock("../api/client", () => ({
  getHealth: () => Promise.resolve({ ok: true, model: "", replay: null, backends: {} }),
  listComplaints: () => Promise.resolve([]),
  listCapas: () => Promise.resolve([]),
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

  it("moves the persona out of the header to the bottom of the sidebar", () => {
    renderShell();
    expect(screen.getByText("Priya R.")).toBeTruthy();
    expect(screen.getByText("Quality Engineer")).toBeTruthy();
  });

  it("drops the removed footer wording and shows a quiet 'Demo data' chip instead", () => {
    renderShell();
    expect(screen.queryByText(/Synthetic demo data/)).toBeNull();
    expect(screen.queryByText(/Built with Gemini/)).toBeNull();
    expect(screen.getByText("Demo data")).toBeTruthy();
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
