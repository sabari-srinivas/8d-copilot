// TypeScript mirrors of backend/agent/models.py — field-for-field. Keep these two
// files in sync; the contract test on the Python side guards its half, this file
// guards the TypeScript half. See docs/contract/README.md.

export type DefectType =
  | "solder_bridge"
  | "missing_component"
  | "misalignment"
  | "scratch"
  | "contamination"
  | "other"
  | "none";

export type Severity = "critical" | "major" | "minor" | "none";
export type Verdict = "supported" | "rejected" | "inconclusive";
export type Direction = "higher" | "lower" | "any";
export type SixM = "Machine" | "Method" | "Material" | "Man" | "Measurement" | "Environment";

// `failed` is deliberate: a crashed investigation stores this instead of spinning
// on `running` forever. Every consumer of `status` must handle it.
export type Status = "running" | "draft_ready" | "approved" | "insufficient_evidence" | "failed";

export type ActionKind = "capa" | "hold" | "work_order" | "customer_reply";
export type AgentName = "intake" | "vision" | "investigator" | "evidence" | "writer" | "system";
export type EventType =
  | "step_started"
  | "tool_call"
  | "tool_result"
  | "memory_hit"
  | "hypothesis"
  | "hypothesis_result"
  | "citation"
  | "draft_ready"
  | "done"
  | "error";

export interface Complaint {
  complaint_id: string;
  customer: string;
  product: string;
  lot_id: string;
  defect: string;
  qty_affected: number | null;
  qty_shipped: number | null;
  received: string;
  eight_d_due: string;
  status: "open" | "closed";
  text: string;
  due_in_working_days: number | null;
}

export interface Defect {
  type: DefectType;
  severity: Severity;
  box: [number, number, number, number];
  confidence: number;
  visual_evidence: string;
}

export interface Hypothesis {
  id: string;
  category: SixM;
  text: string;
  parameter: string | null;
  event_wo_id: string | null;
  direction: Direction;
}

export interface HypothesisResult {
  hypothesis_id: string;
  verdict: Verdict;
  test: string;
  p_value: number;
  effect: string;
  effect_value: number;
  effect_unit: string;
  n_defect: number;
  n_good: number;
  group_labels: string[];
  chart_url: string | null;
}

export interface Citation {
  label: string;
  source: string;
  ref: string;
  quote: string;
}

export interface EightDSection {
  text: string;
  citations: Citation[];
}

export interface EightD {
  D1: EightDSection;
  D2: EightDSection;
  D3: EightDSection;
  D4: EightDSection;
  D5: EightDSection;
  D6: EightDSection;
  D7: EightDSection;
  D8: EightDSection;
}

export interface ProposedAction {
  id: string;
  kind: ActionKind;
  summary: string;
  payload: Record<string, unknown>;
}

export interface MemoryEntry {
  id: string;
  defect_type: string;
  root_cause: string;
  parameter: string;
  line: string;
  capa_id: string;
  lot_id: string;
  investigation_id: string;
  created: string;
}

export interface TravelerRow {
  lot_id: string;
  date: string;
  shift: string;
  operator_id: string;
  reflow_peak_temp_c: number | null;
  time_above_liquidus_s: number | null;
  aoi_bridges: number | null;
  remarks: string;
  low_confidence_fields: string[];
}

export interface Investigation {
  id: string;
  status: Status;
  complaint_id: string;
  lot_id: string;
  created: string;
  photo_url: string;
  defect: Defect | null;
  hypotheses: Hypothesis[];
  results: HypothesisResult[];
  citations: Citation[];
  traveler_rows: TravelerRow[];
  hold_lots: string[];
  eight_d: EightD | null;
  proposed_actions: ProposedAction[];
  memory_hits: MemoryEntry[];
  missing_data: string[];
  approver: string;
  chart_url: string | null;
}

export interface AgentEvent {
  seq: number;
  ts: string;
  agent: AgentName;
  type: EventType;
  title: string;
  detail: string;
  data: Record<string, unknown>;
}

export interface ApproveBody {
  approver: string;
  edits: Record<string, string>;
  rejected_action_ids: string[];
  note: string;
}

export interface ApproveResult {
  capa_id: string | null;
  hold_id: string | null;
  work_order_id: string | null;
  replies: { ja: string; en: string } | null;
  memory_id: string | null;
}

export interface CreateInvestigationResult {
  id: string;
  status: Status;
}

export interface HealthResult {
  ok: boolean;
  model: string;
  backends: {
    plant: string;
    state: string;
    docs: string;
    files: string;
  };
}
