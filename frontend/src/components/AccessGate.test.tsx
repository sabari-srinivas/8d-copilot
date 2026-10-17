import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearDemoCode, getDemoCode } from "../api/demoCode";
import { AccessGate } from "./AccessGate";

// USE_MOCKS is mutable per test so both the gated and ungated (local dev / mock
// mode) paths can be exercised — see client.test usage pattern in Review.test.tsx.
let useMocks = false;
vi.mock("../api/client", () => ({
  get USE_MOCKS() {
    return useMocks;
  },
}));

describe("AccessGate", () => {
  beforeEach(() => {
    useMocks = false;
    clearDemoCode();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    clearDemoCode();
  });

  it("blocks the app behind a code form when locked", () => {
    render(
      <AccessGate>
        <div>secret content</div>
      </AccessGate>,
    );
    expect(screen.queryByText("secret content")).toBeNull();
    expect(screen.getByPlaceholderText("Access code")).not.toBeNull();
  });

  it("shows an error and stays locked on a rejected code", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);
    render(
      <AccessGate>
        <div>secret content</div>
      </AccessGate>,
    );
    fireEvent.change(screen.getByPlaceholderText("Access code"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    await waitFor(() => expect(screen.getByRole("alert")).not.toBeNull());
    expect(screen.queryByText("secret content")).toBeNull();
    expect(getDemoCode()).toBeNull();
  });

  it("unlocks and remembers the code on success", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);
    render(
      <AccessGate>
        <div>secret content</div>
      </AccessGate>,
    );
    fireEvent.change(screen.getByPlaceholderText("Access code"), { target: { value: "let-me-in" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    await waitFor(() => expect(screen.queryByText("secret content")).not.toBeNull());
    expect(getDemoCode()).toBe("let-me-in");
    // The check hit a real gated endpoint with the header, not a client-side guess.
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/complaints"),
      expect.objectContaining({ headers: { "X-Demo-Code": "let-me-in" } }),
    );
  });

  it("skips the gate entirely in mock mode", () => {
    useMocks = true;
    render(
      <AccessGate>
        <div>secret content</div>
      </AccessGate>,
    );
    expect(screen.queryByText("secret content")).not.toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});
