import { mockApproval, mockComplaints, mockInvestigation, mockMemory } from "./mocks";
import type {
  ApproveBody,
  ApproveResult,
  Complaint,
  CreateInvestigationResult,
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

export const listComplaints = (): Promise<Complaint[]> =>
  USE_MOCKS ? mockComplaints() : json<Complaint[]>("/complaints");

export const getInvestigation = (id: string): Promise<Investigation> =>
  USE_MOCKS ? mockInvestigation() : json<Investigation>(`/investigations/${id}`);

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
