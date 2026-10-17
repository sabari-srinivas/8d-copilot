// Mock data for VITE_USE_MOCKS=true. mock_investigation.json and mock_events.json come
// from docs/contract (fixed, validated against the Pydantic models by a backend test —
// never edit them). The complaint inbox and the approval result aren't part of that
// contract fixture set, so they're synthesized here from the same synthetic plant
// (Sree Electronics / Hoshino Denso / Kaveri Motors, all fictional) for a coherent demo.
import mockInvestigationJson from "@contract/mock_investigation.json";
import type {
  ApproveResult,
  CapaRecord,
  Complaint,
  DashboardSummary,
  EightD,
  Investigation,
  MaintenanceEvent,
  MemoryEntry,
  PlantLot,
} from "./types";

function blankSection(text: string) {
  return { text, citations: [] };
}

const REJECTED_8D_OPERATOR_ERROR: EightD = {
  D1: blankSection("Team: SMT process engineer (lead), quality engineer, production shift supervisor."),
  D2: blankSection("Problem description: Hoshino Denso (fictional) reported solder bridging on ECU-PCB-7, lot L2612, found at incoming inspection."),
  D3: blankSection("Containment: lot L2612 and the two adjacent lots were pulled and 100% re-inspected under magnification; bridged boards were reworked."),
  D4: blankSection("Root cause: operator error. Operator OP-17, who began running Line 2 shortly before the affected lots, did not consistently follow the stencil wipe procedure, resulting in excess solder deposit and bridging at fine-pitch pads."),
  D5: blankSection("Permanent corrective action: OP-17 was retrained on the stencil wipe procedure and re-certified."),
  D6: blankSection("Verification of effectiveness: no further bridging was observed on OP-17's lots in the week following retraining."),
  D7: blankSection("Prevent recurrence: training records updated to reflect re-certification."),
  D8: blankSection("Closure: corrective action verified and closed; 8D sent to Hoshino Denso (fictional)."),
};

const REJECTED_8D_MISSING_DETECTION: EightD = {
  D1: blankSection("Team: SMT process engineer (lead), quality engineer, reflow equipment technician."),
  D2: blankSection("Problem description: Meridian Auto Electronics (fictional) reported solder bridging on ECU-PCB-7, lot L2610, found at incoming inspection."),
  D3: blankSection("Containment: lot L2610 and lots produced in the same window on Line 2 were pulled and 100% re-inspected; bridged boards were reworked."),
  D4: {
    text: "Root cause: following work order WO-388 (Line 2 reflow oven zone 7 heater replacement and profile re-tune), reflow peak temperature drifted above the process limit across the lots produced afterward, causing excess solder flow and bridging between adjacent fine-pitch pads [PFMEA row 14].",
    citations: [{ label: "PFMEA row 14", source: "pfmea.md", ref: "Row 14", quote: "Cause: Reflow peak temperature above profile limit." }],
  },
  D5: blankSection("Permanent corrective action: re-qualify the Line 2 reflow profile and hold lots produced since the last verified profile."),
  D6: blankSection("Verification of effectiveness: profile re-qualification to be confirmed against the 235-250 °C specification before the hold is released."),
  D7: blankSection("Prevent recurrence: PFMEA row 14 and control plan item 6 to be reviewed."),
  D8: blankSection("Closure: corrective action pending verification; 8D sent to Meridian Auto Electronics (fictional)."),
};

// Field-for-field with backend/data/generate_plant.py's seed complaints (five open, two
// of them rejections — CR #6/#14) so the mock inbox (VITE_USE_MOCKS=true) demos the same
// story as the live backend.
const MOCK_COMPLAINTS: Complaint[] = [
  {
    complaint_id: "C-2026-031",
    customer: "Hoshino Denso (fictional)",
    product: "ECU-PCB-7",
    lot_id: "L2611",
    defect: "solder_bridge",
    qty_affected: 14,
    qty_shipped: 500,
    received: "2026-10-15",
    eight_d_due: "2026-10-29",
    status: "open",
    text: "Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units at our incoming/ICT. Please contain immediately and send 8D within 10 working days.",
    due_in_working_days: 8,
    is_rejection: false,
    objection: "",
    original_eight_d: null,
  },
  {
    complaint_id: "C-2026-033",
    customer: "Hoshino Denso (fictional)",
    product: "ECU-PCB-7",
    lot_id: "L2612",
    defect: "solder_bridge",
    qty_affected: 7,
    qty_shipped: 515,
    received: "2026-10-16",
    eight_d_due: "2026-10-20",
    status: "open",
    text: "We are returning the 8D for lot L2612 (7 of 515 units, solder bridging at incoming inspection) unapproved: root cause stated as operator error; not acceptable. Please re-investigate with objective evidence and resubmit within 3 working days.",
    due_in_working_days: 2,
    is_rejection: true,
    objection: "root cause stated as operator error; not acceptable",
    original_eight_d: REJECTED_8D_OPERATOR_ERROR,
  },
  {
    complaint_id: "C-2026-032",
    customer: "Kaveri Motors (fictional)",
    product: "ECU-PCB-9",
    lot_id: "L9142",
    defect: "tombstoning",
    qty_affected: 3,
    qty_shipped: 1200,
    received: "2026-10-14",
    eight_d_due: "2026-10-28",
    status: "open",
    text: "3 boards with tombstoned 0402 capacitors at C112, lot 9142. Request 8D.",
    due_in_working_days: 7,
    is_rejection: false,
    objection: "",
    original_eight_d: null,
  },
  {
    complaint_id: "C-2026-034",
    customer: "Meridian Auto Electronics (fictional)",
    product: "ECU-PCB-7",
    lot_id: "L2610",
    defect: "solder_bridge",
    qty_affected: 13,
    qty_shipped: 511,
    received: "2026-10-15",
    eight_d_due: "2026-10-30",
    status: "open",
    text: "We are returning the 8D for lot L2610 (13 of 511 units, solder bridging at incoming inspection) unapproved: D4 does not explain why the condition escaped detection. Please revise and resubmit.",
    due_in_working_days: 9,
    is_rejection: true,
    objection: "D4 does not explain why the condition escaped detection",
    original_eight_d: REJECTED_8D_MISSING_DETECTION,
  },
  {
    complaint_id: "C-2026-035",
    customer: "Vindhya Auto Systems (fictional)",
    product: "ECU-PCB-7",
    lot_id: "L2590",
    defect: "missing_component",
    qty_affected: 1,
    qty_shipped: null,
    received: "2026-10-13",
    eight_d_due: "2026-11-06",
    status: "open",
    text: "One missing 0402 resistor at position R18 found on ECU-PCB-7, lot 2590, during customer incoming inspection. Please investigate and provide 8D.",
    due_in_working_days: 14,
    is_rejection: false,
    objection: "",
    original_eight_d: null,
  },
  {
    complaint_id: "C-2026-024",
    customer: "Hoshino Denso (fictional)",
    product: "ECU-PCB-7",
    lot_id: "L2389",
    defect: "tombstoning",
    qty_affected: 5,
    qty_shipped: 800,
    received: "2026-07-02",
    eight_d_due: "2026-07-16",
    status: "closed",
    text: "Tombstoning on 0402 resistors, lot 2389.",
    due_in_working_days: null,
    is_rejection: false,
    objection: "",
    original_eight_d: null,
  },
  // Five more past investigations (data/constants.py's PAST_INVESTIGATIONS on the
  // live backend) so "Past investigations" reads as populated in mock mode too.
  {
    complaint_id: "C-2026-012", customer: "Vindhya Auto Systems (fictional)", product: "ECU-PCB-7",
    lot_id: "L2567", defect: "contamination", qty_affected: 2, qty_shipped: 498,
    received: "2026-07-20", eight_d_due: "2026-08-03", status: "closed",
    text: "Flux residue found under components on ECU-PCB-7, lot 2567, 2 of 498 units at incoming inspection. Please investigate and provide 8D.",
    due_in_working_days: null, is_rejection: false, objection: "", original_eight_d: null,
  },
  {
    complaint_id: "C-2026-015", customer: "Meridian Auto Electronics (fictional)", product: "ECU-PCB-7",
    lot_id: "L2578", defect: "misalignment", qty_affected: 4, qty_shipped: 503,
    received: "2026-08-05", eight_d_due: "2026-08-19", status: "closed",
    text: "Component misalignment on ECU-PCB-7, lot 2578, 4 of 503 units found at AOI. Please investigate and provide 8D.",
    due_in_working_days: null, is_rejection: false, objection: "", original_eight_d: null,
  },
  {
    complaint_id: "C-2026-019", customer: "Hoshino Denso (fictional)", product: "ECU-PCB-7",
    lot_id: "L2585", defect: "missing_component", qty_affected: 1, qty_shipped: 501,
    received: "2026-08-22", eight_d_due: "2026-09-05", status: "closed",
    text: "Missing 0402 resistor at position R18 on ECU-PCB-7, lot 2585, 1 of 501 units found at customer incoming inspection. Please investigate and provide 8D.",
    due_in_working_days: null, is_rejection: false, objection: "", original_eight_d: null,
  },
  {
    complaint_id: "C-2026-022", customer: "Kaveri Motors (fictional)", product: "ECU-PCB-7",
    lot_id: "L2592", defect: "solder_bridge", qty_affected: 6, qty_shipped: 497,
    received: "2026-09-02", eight_d_due: "2026-09-16", status: "closed",
    text: "Solder bridging on ECU-PCB-7, lot 2592, 6 of 497 units found at incoming inspection. Please contain and provide 8D.",
    due_in_working_days: null, is_rejection: false, objection: "", original_eight_d: null,
  },
  {
    complaint_id: "C-2026-026", customer: "Araku Components (fictional)", product: "ECU-PCB-7",
    lot_id: "L2599", defect: "scratch", qty_affected: 3, qty_shipped: 505,
    received: "2026-09-10", eight_d_due: "2026-09-24", status: "closed",
    text: "PCB edge scratches on ECU-PCB-7, lot 2599, 3 of 505 units found at incoming inspection. Please investigate and provide 8D.",
    due_in_working_days: null, is_rejection: false, objection: "", original_eight_d: null,
  },
];

const MOCK_MEMORY: MemoryEntry[] = [
  {
    id: "MEM-0098",
    defect_type: "tombstoning",
    root_cause: "Paste past its working window",
    parameter: "paste_age_h",
    line: "L1",
    capa_id: "CAPA-0098",
    lot_id: "L2389",
    investigation_id: "inv_hist_0024",
    created: "2026-07-10T00:00:00+00:00",
  },
  {
    id: "MEM-0083", defect_type: "contamination",
    root_cause: "Flux residue from an overdue stencil-cleaning cycle on Line 1.",
    parameter: "squeegee_pressure_kg", line: "L1", capa_id: "CAPA-0083", lot_id: "L2567",
    investigation_id: "inv_hist_0012", created: "2026-07-25T00:00:00+00:00",
  },
  {
    id: "MEM-0088", defect_type: "misalignment",
    root_cause: "Stencil-to-board registration drift from worn fiducial clamps on Line 2.",
    parameter: "stencil_print_count", line: "L2", capa_id: "CAPA-0088", lot_id: "L2578",
    investigation_id: "inv_hist_0015", created: "2026-08-10T00:00:00+00:00",
  },
  {
    id: "MEM-0091", defect_type: "missing_component",
    root_cause: "Feeder 9 intermittent jam dropping 0402 resistors on Line 1.",
    parameter: "", line: "L1", capa_id: "CAPA-0091", lot_id: "L2585",
    investigation_id: "inv_hist_0019", created: "2026-08-27T00:00:00+00:00",
  },
  {
    id: "MEM-0094", defect_type: "solder_bridge",
    root_cause: "Paste exceeded its working window on second shift, Line 2.",
    parameter: "paste_age_h", line: "L2", capa_id: "CAPA-0094", lot_id: "L2592",
    investigation_id: "inv_hist_0022", created: "2026-09-05T00:00:00+00:00",
  },
  {
    id: "MEM-0097", defect_type: "scratch",
    root_cause: "Misaligned conveyor guide rail scoring board edges on Line 1.",
    parameter: "conveyor_speed_cm_min", line: "L1", capa_id: "CAPA-0097", lot_id: "L2599",
    investigation_id: "inv_hist_0026", created: "2026-09-12T00:00:00+00:00",
  },
];

export function mockComplaints(): Promise<Complaint[]> {
  return Promise.resolve(MOCK_COMPLAINTS);
}

export function mockInvestigation(): Promise<Investigation> {
  return Promise.resolve(mockInvestigationJson as unknown as Investigation);
}

export function mockMemory(): Promise<MemoryEntry[]> {
  return Promise.resolve(MOCK_MEMORY);
}

// ---------------------------------------------------------------------------
// Dashboard / CAPA / Plant mocks (VITE_USE_MOCKS=true, no backend running).
// Deterministic -- same shape and story as the live data/generate_plant.py seed
// (64 lots L2551-L2614, Line 2 drift after WO-388 on 2026-10-08) but built here with
// plain arithmetic, not a port of the real RNG -- this is a coherent demo fixture,
// not a correctness fixture (the dashboard.py tests on the backend own that job).
// ---------------------------------------------------------------------------
const WO388_DATE = "2026-10-08";
const DRIFT_LOTS = new Set(["L2609", "L2610", "L2611", "L2612", "L2613", "L2614"]);

function mockLots(): PlantLot[] {
  const lots: PlantLot[] = [];
  const start = new Date("2026-09-14T00:00:00Z");
  for (let i = 0; i < 64; i++) {
    const num = 2551 + i;
    const lotId = `L${num}`;
    const date = new Date(start);
    date.setUTCDate(date.getUTCDate() + Math.floor(i / 2));
    const drift = DRIFT_LOTS.has(lotId);
    const line = drift ? "L2" : i % 2 === 0 ? "L1" : "L2";
    const bridges = lotId === "L2611" ? 14 : drift ? 13 : (i % 2 === 0 ? 2 : 1);
    const qty = 500;
    lots.push({
      lot_id: lotId, line, shift: "ABC"[i % 3], date: date.toISOString().slice(0, 10),
      product: "ECU-PCB-7", qty, paste_lot: `PL-${2601 + Math.floor(i / 7)}`,
      stencil_id: line === "L1" ? "ST-03A" : date.toISOString().slice(0, 10) >= "2026-10-07" ? "ST-07B" : "ST-05A",
      operator_id: line === "L1" ? "OP-04" : "OP-11",
      defects_solder_bridge: bridges, defects_other: i % 5 === 0 ? 2 : 1,
      bridge_rate: Math.round((bridges / qty) * 10000) / 10000,
      ship_status: ["L2613", "L2614"].includes(lotId) ? "in_warehouse" : "shipped",
      reflow_peak_temp_c: drift ? 253.2 : 245.0,
      time_above_liquidus_s: drift ? 82 : 62, preheat_ramp_c_per_s: 1.6, soak_time_s: 85,
      conveyor_speed_cm_min: line === "L1" ? 78 : 80, paste_age_h: 10, room_humidity_pct: 52,
      stencil_print_count: 20000, squeegee_pressure_kg: 6.0,
    });
  }
  return lots;
}

const MOCK_LOTS = mockLots();

const MOCK_MAINTENANCE: MaintenanceEvent[] = [
  { wo_id: "WO-371", line: "L1", date: "2026-09-16", asset: "Pick-and-place head 2", description: "Nozzle set replaced (wear)", status: "closed", post_check: "profile_check_na" },
  { wo_id: "WO-374", line: "L2", date: "2026-09-19", asset: "Stencil printer", description: "Squeegee blade replaced", status: "closed", post_check: "n/a" },
  { wo_id: "WO-377", line: "L1", date: "2026-09-23", asset: "Reflow oven", description: "Quarterly PM: conveyor chain lubrication, fan check", status: "closed", post_check: "profile_verified" },
  { wo_id: "WO-379", line: "L2", date: "2026-09-25", asset: "AOI station", description: "Camera recalibration", status: "closed", post_check: "n/a" },
  { wo_id: "WO-381", line: "L1", date: "2026-09-29", asset: "Nitrogen generator", description: "Filter change", status: "closed", post_check: "n/a" },
  { wo_id: "WO-383", line: "L2", date: "2026-10-02", asset: "Reflow oven", description: "Quarterly PM: conveyor chain lubrication, fan check", status: "closed", post_check: "profile_verified" },
  { wo_id: "WO-386", line: "L2", date: "2026-10-07", asset: "Stencil printer", description: "New stencil ST-07B installed for ECU-PCB-7 (replaces ST-05A)", status: "closed", post_check: "first_article_ok" },
  { wo_id: "WO-388", line: "L2", date: WO388_DATE, asset: "Reflow oven zone 7", description: "Zone 7 heater element replaced, profile re-tuned by vendor", status: "closed", post_check: "profile_verification_pending" },
  { wo_id: "WO-390", line: "L1", date: "2026-10-10", asset: "Pick-and-place feeder bank", description: "Feeder 14 jam cleared", status: "closed", post_check: "n/a" },
  { wo_id: "WO-392", line: "L2", date: "2026-10-12", asset: "Conveyor", description: "Board stop sensor cleaned", status: "closed", post_check: "n/a" },
];

function avgPct(line: string): number {
  const sub = MOCK_LOTS.filter((l) => l.line === line);
  return Math.round((sub.reduce((s, l) => s + l.bridge_rate, 0) / sub.length) * 100 * 100) / 100;
}

const MOCK_CAPAS: CapaRecord[] = [
  {
    id: "CAPA-0098", investigation_id: "inv_hist_0024", complaint_id: "C-2026-024",
    lot_id: "L2389", root_cause: "Paste past its working window", owner: "Quality Manager",
    opened: "2026-07-10", status: "closed", summary: "Paste-age control procedure for tombstoning.",
    approver: "Priya R.", note: "", defect_type: "tombstoning", line: "L1", memory_id: "MEM-0098",
    effectiveness: {
      capa_id: "CAPA-0098", defect_type: "tombstoning", line: "L1", implemented_on: "2026-07-10",
      verdict: "never_worked", test: "Welch t-test", p_value: 0.4816,
      effect: "1.8% right after CAPA-0098, barely moved from 2.0% before it (p=0.4816) -- signed off, never actually fixed",
      effect_value: -0.0019, effect_unit: "defect rate", n_before: 10, n_immediate: 7, n_recent: 7,
      group_labels: ["Before CAPA-0098 (implemented 2026-07-10)", "Immediately after CAPA-0098", "Recent, after CAPA-0098"],
      before_rate: 0.02, immediate_rate: 0.0182, recent_rate: 0.014, p_immediate: 0.4816, p_recent: 0.0545,
      chart_url: null,
    },
  },
  {
    id: "CAPA-0083", investigation_id: "inv_hist_0012", complaint_id: "C-2026-012",
    lot_id: "L2567", root_cause: "Flux residue from an overdue stencil-cleaning cycle on Line 1.",
    owner: "Quality Manager", opened: "2026-07-25", status: "closed",
    summary: "Contamination corrective action.", approver: "Priya R.", note: "",
    defect_type: "contamination", line: "L1", memory_id: "MEM-0083",
    effectiveness: {
      capa_id: "CAPA-0083", defect_type: "contamination", line: "L1", implemented_on: "2026-07-25",
      verdict: "insufficient_data", test: "Welch t-test", p_value: null,
      effect: "only 0 lot(s) before, 3 immediately after and 3 recent lot(s) of CAPA-0083 on L1 -- too few to test",
      effect_value: null, effect_unit: "defect rate", n_before: 0, n_immediate: 3, n_recent: 3,
      group_labels: ["Before CAPA-0083 (implemented 2026-07-25)", "Immediately after CAPA-0083", "Recent, after CAPA-0083"],
      before_rate: null, immediate_rate: null, recent_rate: null, p_immediate: null, p_recent: null,
      chart_url: null,
    },
  },
  {
    id: "CAPA-0088", investigation_id: "inv_hist_0015", complaint_id: "C-2026-015",
    lot_id: "L2578", root_cause: "Stencil-to-board registration drift from worn fiducial clamps on Line 2.",
    owner: "Quality Manager", opened: "2026-08-10", status: "closed",
    summary: "Misalignment corrective action.", approver: "Priya R.", note: "",
    defect_type: "misalignment", line: "L2", memory_id: "MEM-0088", effectiveness: null,
  },
  {
    id: "CAPA-0091", investigation_id: "inv_hist_0019", complaint_id: "C-2026-019",
    lot_id: "L2585", root_cause: "Feeder 9 intermittent jam dropping 0402 resistors on Line 1.",
    owner: "Quality Manager", opened: "2026-08-27", status: "closed",
    summary: "Missing component corrective action.", approver: "Priya R.", note: "",
    defect_type: "missing_component", line: "L1", memory_id: "MEM-0091", effectiveness: null,
  },
  {
    id: "CAPA-0094", investigation_id: "inv_hist_0022", complaint_id: "C-2026-022",
    lot_id: "L2592", root_cause: "Paste exceeded its working window on second shift, Line 2.",
    owner: "Quality Manager", opened: "2026-09-05", status: "closed",
    summary: "Solder bridge corrective action.", approver: "Priya R.", note: "",
    defect_type: "solder_bridge", line: "L2", memory_id: "MEM-0094", effectiveness: null,
  },
  {
    id: "CAPA-0097", investigation_id: "inv_hist_0026", complaint_id: "C-2026-026",
    lot_id: "L2599", root_cause: "Misaligned conveyor guide rail scoring board edges on Line 1.",
    owner: "Quality Manager", opened: "2026-09-12", status: "closed",
    summary: "Scratch corrective action.", approver: "Priya R.", note: "",
    defect_type: "scratch", line: "L1", memory_id: "MEM-0097", effectiveness: null,
  },
];

function mockDashboardSummaryData(): DashboardSummary {
  const toPoint = (l: PlantLot) => ({ lot_id: l.lot_id, date: l.date, rate_pct: Math.round(l.bridge_rate * 10000) / 100 });
  return {
    first_pass_yield: { units: 31973, defects: 282, pct: 99.12 },
    open_eight_ds: { count: 5, soonest_due_working_days: 2 },
    capas: { open: 0, recurrence_rate: 1.0, n_evaluated: 1 },
    lots_on_hold: 0,
    charts: {
      defect_rate_by_line: {
        line1: MOCK_LOTS.filter((l) => l.line === "L1").map(toPoint),
        line2: MOCK_LOTS.filter((l) => l.line === "L2").map(toPoint),
        line1_avg_pct: avgPct("L1"), line2_avg_pct: avgPct("L2"),
        marker_date: WO388_DATE, marker_label: "WO-388",
      },
      defect_pareto: { solder_bridge: 188, other: 94 },
      spc_reflow_peak: {
        limit_c: 250.0,
        points: MOCK_LOTS.map((l) => ({ lot_id: l.lot_id, date: l.date, value: l.reflow_peak_temp_c })),
      },
    },
  };
}

export function mockDashboardSummary(): Promise<DashboardSummary> {
  return Promise.resolve(mockDashboardSummaryData());
}

export function mockCapas(): Promise<CapaRecord[]> {
  return Promise.resolve(MOCK_CAPAS);
}

export function mockPlantLots(): Promise<PlantLot[]> {
  return Promise.resolve(MOCK_LOTS);
}

export function mockPlantMaintenance(): Promise<MaintenanceEvent[]> {
  return Promise.resolve(MOCK_MAINTENANCE);
}

export function mockApproval(): Promise<ApproveResult> {
  return Promise.resolve({
    capa_id: "CAPA-0142",
    hold_id: "HOLD-0091",
    work_order_id: "WO-412",
    memory_id: "MEM-021",
    replies: {
      ja: "星野電装 御中\n\n平素より格別のお引き立てを賜り、厚く御礼申し上げます。\n\n貴社より御報告いただきました ECU-PCB-7、ロット L2611 におけるはんだブリッジ不具合について、原因調査が完了いたしましたのでご報告申し上げます。\n\n【原因】\nライン2のリフロー工程において、作業指示書 WO-388 によるプロファイル変更後、ピーク温度の検証が未実施のまま生産が再開されたため、はんだ付けピーク温度が規定範囲(235–250℃)を超えて上昇し、隣接する微細ピッチパッド間にはんだブリッジが発生いたしました。\n\n【是正処置】\n該当生産期間のロット(L2609〜L2614)を出荷保留とし、是正措置番号 CAPA-0142 のもとでリフロープロファイルの再検証・再適格化を実施いたします(作業指示書 WO-412)。\n\nご迷惑をおかけしましたことを深くお詫び申し上げます。今後このような事象が再発せぬよう、工程変更後のプロファイル検証をコントロールプランに明記し、徹底してまいります。\n\n敬具",
      en: "Dear Hoshino Denso,\n\nThank you for your continued business and for reporting this issue.\n\nWe have completed our investigation into the solder bridging defect on ECU-PCB-7, lot L2611, and share our findings below.\n\nRoot cause: Following work order WO-388 (a reflow profile change on Line 2), the required post-change profile verification was not completed before production resumed. As a result, reflow peak temperature drifted above the qualified profile limit (235-250 degC), causing excess solder flow and bridging between adjacent fine-pitch pads.\n\nCorrective action: Lots produced during the affected window (L2609-L2614) have been placed on hold. Under CAPA-0142, we are re-qualifying the Line 2 reflow profile and confirming it returns within specification before the hold is released (work order WO-412). The control plan is being updated to require sign-off evidence of profile verification after any reflow profile change.\n\nWe apologize for the inconvenience this has caused and are committed to preventing recurrence.\n\nSincerely,\nSree Electronics Quality Team",
    },
    rejected_action_ids: [],
  });
}
