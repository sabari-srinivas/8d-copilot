import { mockApproval, mockComplaints, mockInvestigation, mockMemory } from "./mocks";
import type {
  ApproveBody,
  ApproveResult,
  Complaint,
  CreateInvestigationResult,
  HealthResult,
  Investigation,
  MemoryEntry,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return res.json() as Promise<T>;
}

/** The backend hands back file paths relative to its own origin — `/api/files/...`
 * (local files backend) — under `photo_url` and `chart_url`. In dev the frontend
 * and the API run on different origins (Vite on 5173, uvicorn on 8000), so a bare
 * `<img src>` 404s against the frontend's own origin. Every place a URL from the
 * API reaches an `src`/`href` must go through this first. A value that is already
 * absolute (http(s):, data:, blob: — e.g. an uploaded-but-not-yet-saved preview)
 * passes through unchanged; mock fixtures using the same relative shape degrade to
 * the components' own "not available" fallback, same as before. */
export function resolveApiUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^[a-z][a-z0-9+.-]*:/i.test(path)) return path; // absolute: http(s), data, blob...
  return `${BASE}${path}`;
}

export const listComplaints = (): Promise<Complaint[]> =>
  USE_MOCKS ? mockComplaints() : json<Complaint[]>("/complaints");

export const getInvestigation = (id: string): Promise<Investigation> =>
  USE_MOCKS ? mockInvestigation() : json<Investigation>(`/investigations/${id}`);

/** The writer publishes the `draft_ready` SSE event from inside its own `run()`,
 * before the orchestrator's `inv.eight_d = ...; state.save_investigation(inv)`
 * that follows it (backend/agent/orchestrator.py) — so a client that reacts to the
 * event by immediately calling `GET /investigations/{id}` can race the save and
 * read a draft-less `draft_ready`, or an `insufficient_evidence` before
 * `missing_data` landed. This isn't a mock artifact; it only shows up against the
 * live backend. Pages that render the 8D should fetch through here (instead of
 * `getInvestigation` directly) whenever the fetch is triggered by `draft_ready`
 * arriving over SSE rather than by an unconditional poll — `isReady` says what
 * "the data this screen needs is actually here" means for that screen. */
export async function getInvestigationReady(
  id: string,
  isReady: (inv: Investigation) => boolean,
  { retries = 10, delayMs = 250 }: { retries?: number; delayMs?: number } = {},
): Promise<Investigation> {
  let inv = await getInvestigation(id);
  for (let i = 0; i < retries && inv.status !== "failed" && !isReady(inv); i++) {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    inv = await getInvestigation(id);
  }
  return inv;
}

export const createInvestigation = async (
  form: FormData,
): Promise<CreateInvestigationResult> =>
  USE_MOCKS
    ? { id: "inv_mock", status: "running" }
    : json<CreateInvestigationResult>("/investigations", { method: "POST", body: form });

export const approve = (id: string, body: ApproveBody): Promise<ApproveResult> =>
  USE_MOCKS
    ? mockApproval()
    : json<ApproveResult>(`/investigations/${id}/approve`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });

export const listMemory = (): Promise<MemoryEntry[]> =>
  USE_MOCKS ? mockMemory() : json<MemoryEntry[]>("/memory");

/** Health is advisory — callers must tolerate failure. In mock mode there is no backend,
 * so report a live (non-replay) run rather than pretending to know. */
export const getHealth = (): Promise<HealthResult> =>
  USE_MOCKS
    ? Promise.resolve({
        ok: true,
        model: "",
        replay: null,
        backends: { plant: "mock", state: "mock", docs: "mock", files: "mock" },
      })
    : json<HealthResult>("/health");
