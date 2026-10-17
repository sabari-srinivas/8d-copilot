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
export type AgentName =
  | "intake"
  | "vision"
  | "investigator"
  | "evidence"
  | "writer"
  | "reviser"
  | "system";
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
  /** True when this complaint is the customer's rejection of an 8D already submitted,
   * not a new defect report (CR #14) — the inbox and the "new investigation" screen
   * both branch on this, and the backend routes the investigation through the revise
   * path (agent "reviser") rather than drafting fresh. */
  is_rejection: boolean;
  /** The customer's stated reason for rejecting, e.g. "root cause stated as operator
   * error; not acceptable". Empty for an ordinary complaint. */
  objection: string;
  /** The full D1-D8 text of the 8D being rejected, in the same shape as `EightD`.
   * `null` for an ordinary complaint. */
  original_eight_d: EightD | null;
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

/** Extracted from an optional shift-lead voice-note upload (CR #12) by
 * `agent/tools/voice_tool.py`, Gemini's native audio understanding -- no separate
 * speech-to-text step. `language`/`language_name` report whatever language was heard
 * (never forced to English); `translation` is always an English rendering, equal to
 * `transcript` when the note is already in English. `low_confidence_fields` names any
 * of `lot_or_line`/`observations`/`maintenance_mentions` the model is not sure it heard
 * correctly -- same convention as `TravelerRow.low_confidence_fields`. */
export interface VoiceNote {
  language: string;
  language_name: string;
  transcript: string;
  translation: string;
  lot_or_line: string;
  observations: string[];
  maintenance_mentions: string[];
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
  /** Null when no voice note was uploaded with the investigation (CR #12). */
  voice_note: VoiceNote | null;
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
  /** Ids the approver excluded at review. A null `*_id`/`replies` field can mean
   * either "excluded here" or "attempted and failed" (e.g. the customer-reply
   * Gemini call raised) -- check membership here before claiming exclusion. */
  rejected_action_ids: string[];
}

export interface CreateInvestigationResult {
  id: string;
  status: Status;
}

export type CapaVerdict = "worked" | "never_worked" | "regressed" | "insufficient_data";

/** Mirrors backend/agent/models.py's CapaEffectiveness -- did a past CAPA actually
 * reduce the defect rate? Same reporting shape as HypothesisResult, plus the
 * CAPA-specific context and three-window breakdown (before/immediate/recent). */
export interface CapaEffectiveness {
  capa_id: string;
  defect_type: string;
  line: string;
  implemented_on: string;
  verdict: CapaVerdict;
  test: string;
  p_value: number | null;
  effect: string;
  effect_value: number | null;
  effect_unit: string;
  n_before: number;
  n_immediate: number;
  n_recent: number;
  group_labels: string[];
  before_rate: number | null;
  immediate_rate: number | null;
  recent_rate: number | null;
  p_immediate: number | null;
  p_recent: number | null;
  chart_url: string | null;
}

/** GET /api/capas row. `defect_type`/`line`/`memory_id` come from the quality-memory
 * entry this CAPA produced (matched on capa_id) -- a CAPA record itself carries none
 * of them. `effectiveness` is null until both are known. */
export interface CapaRecord {
  id: string;
  investigation_id: string;
  complaint_id: string;
  lot_id: string;
  root_cause: string;
  owner: string;
  opened: string;
  status: string;
  summary: string;
  approver: string;
  note: string;
  defect_type: string;
  line: string;
  memory_id: string;
  effectiveness: CapaEffectiveness | null;
}

export interface FirstPassYield {
  units: number;
  defects: number;
  pct: number;
}

export interface OpenEightDs {
  count: number;
  soonest_due_working_days: number | null;
}

/** `recurrence_rate` is null until at least one CAPA has a determinate effectiveness
 * verdict (not insufficient_data) -- never a fabricated 0%. */
export interface CapaDashboardSummary {
  open: number;
  recurrence_rate: number | null;
  n_evaluated: number;
}

export interface DefectRateByLinePoint {
  lot_id: string;
  date: string;
  rate_pct: number;
}

/** The dashboard's hero chart: defect rate by lot, Line 1 vs Line 2, with a marker at
 * the work order that planted the drift. Rates and averages are already *100
 * (percentages), not fractions. */
export interface DefectRateByLine {
  line1: DefectRateByLinePoint[];
  line2: DefectRateByLinePoint[];
  line1_avg_pct: number;
  line2_avg_pct: number;
  marker_date: string;
  marker_label: string;
}

export interface DefectPareto {
  solder_bridge: number;
  other: number;
}

export interface SpcPoint {
  lot_id: string;
  date: string;
  value: number;
}

export interface SpcReflowPeak {
  limit_c: number;
  points: SpcPoint[];
}

export interface DashboardCharts {
  defect_rate_by_line: DefectRateByLine;
  defect_pareto: DefectPareto;
  spc_reflow_peak: SpcReflowPeak;
}

/** GET /api/dashboard/summary -- every number computed live, never hard-coded. */
export interface DashboardSummary {
  first_pass_yield: FirstPassYield;
  open_eight_ds: OpenEightDs;
  capas: CapaDashboardSummary;
  lots_on_hold: number;
  charts: DashboardCharts;
}

/** GET /api/plant/lots row -- lots.csv joined to process.csv, the full per-lot
 * receipts. Carries operator_id/shift (real plant columns) but the UI must never
 * build an aggregate "defects by operator/shift" view from them. */
export interface PlantLot {
  lot_id: string;
  line: string;
  shift: string;
  date: string;
  product: string;
  qty: number;
  paste_lot: string;
  stencil_id: string;
  operator_id: string;
  defects_solder_bridge: number;
  defects_other: number;
  bridge_rate: number;
  ship_status: string;
  reflow_peak_temp_c: number;
  time_above_liquidus_s: number;
  preheat_ramp_c_per_s: number;
  soak_time_s: number;
  conveyor_speed_cm_min: number;
  paste_age_h: number;
  room_humidity_pct: number;
  stencil_print_count: number;
  squeegee_pressure_kg: number;
}

export interface MaintenanceEvent {
  wo_id: string;
  line: string;
  date: string;
  asset: string;
  description: string;
  status: string;
  post_check: string;
}

export interface HealthResult {
  ok: boolean;
  model: string;
  /** Name of the recorded case being replayed, or null when the run is live.
   * Surfaced as a header chip so a viewer is never unsure which they are watching. */
  replay: string | null;
  backends: {
    plant: string;
    state: string;
    docs: string;
    files: string;
  };
}
