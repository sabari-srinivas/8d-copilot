import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./demoCode", () => ({ getDemoCode: () => "demo-code" }));

let fetchMock: ReturnType<typeof vi.fn>;

function ok(body: unknown) {
  return { ok: true, status: 200, statusText: "OK", json: () => Promise.resolve(body) };
}

beforeEach(() => {
  vi.resetModules();
  fetchMock = vi.fn().mockResolvedValue(ok([]));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

/** Paths, stripped of the origin prefix, in call order. */
function paths() {
  return fetchMock.mock.calls.map((c) => String(c[0]).replace(/^.*\/api/, ""));
}

describe("read caching (CR #18)", () => {
  it("fetches a list once however many times a tab asks for it", async () => {
    const { listCapas } = await import("./client");
    await listCapas();
    await listCapas();
    await listCapas();
    // The point of the change: revisiting a tab must not re-pay the round trip.
    expect(paths().filter((p) => p === "/capas")).toHaveLength(1);
  });

  it("collapses concurrent callers into one request", async () => {
    const { listComplaints } = await import("./client");
    // The sidebar and the Complaints page both ask on mount, in the same tick.
    await Promise.all([listComplaints(), listComplaints(), listComplaints()]);
    expect(paths().filter((p) => p === "/complaints")).toHaveLength(1);
  });

  it("keeps each path's cache separate", async () => {
    const { listCapas, listMemory, getDashboardSummary } = await import("./client");
    await Promise.all([listCapas(), listMemory(), getDashboardSummary()]);
    expect(paths().sort()).toEqual(["/capas", "/dashboard/summary", "/memory"]);
  });

  it("retries after a failure instead of caching the error forever", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 503, statusText: "Unavailable" });
    const { listCapas } = await import("./client");

    await expect(listCapas()).rejects.toThrow(/503/);
    fetchMock.mockResolvedValue(ok([{ id: "CAPA-0142" }]));
    // A cached rejected promise would make one transient 503 look like a permanently
    // broken tab for the rest of the session.
    await expect(listCapas()).resolves.toEqual([{ id: "CAPA-0142" }]);
    expect(paths().filter((p) => p === "/capas")).toHaveLength(2);
  });

  it("warms every tab in one pass, without duplicating anything", async () => {
    const { prefetchAll } = await import("./client");
    prefetchAll();
    prefetchAll();
    await Promise.resolve();
    expect(paths().sort()).toEqual([
      "/capas", "/complaints", "/dashboard/summary", "/memory",
      "/plant/lots", "/plant/maintenance",
    ]);
  });

  it("a tab opened after prefetch reuses the warmed request", async () => {
    const { prefetchAll, listCapas } = await import("./client");
    prefetchAll();
    await listCapas();
    expect(paths().filter((p) => p === "/capas")).toHaveLength(1);
  });

  it("approving drops the cache so the CAPA and Memory tabs show the new records", async () => {
    const { listCapas, approve } = await import("./client");
    await listCapas();
    fetchMock.mockResolvedValue(ok({ capa_id: "CAPA-0144" }));
    await approve("inv_1", { approver: "Priya R.", edits: {}, rejected_action_ids: [], note: "" });

    fetchMock.mockResolvedValue(ok([{ id: "CAPA-0144" }]));
    await expect(listCapas()).resolves.toEqual([{ id: "CAPA-0144" }]);
    expect(paths().filter((p) => p === "/capas")).toHaveLength(2);
  });

  it("does not cache a single investigation, which changes while it runs", async () => {
    const { getInvestigation } = await import("./client");
    fetchMock.mockResolvedValue(ok({ id: "inv_1", status: "running" }));
    await getInvestigation("inv_1");
    await getInvestigation("inv_1");
    // The live screen polls this as the run progresses; caching it would freeze the
    // investigation at "running" forever.
    expect(paths().filter((p) => p === "/investigations/inv_1")).toHaveLength(2);
  });
});
