// Mock data for VITE_USE_MOCKS=true. mock_investigation.json and mock_events.json come
// from docs/contract (fixed, validated against the Pydantic models by a backend test —
// never edit them). The complaint inbox and the approval result aren't part of that
// contract fixture set, so they're synthesized here from the same synthetic plant
// (Sree Electronics / Hoshino Denso / Kaveri Motors, all fictional) for a coherent demo.
import mockInvestigationJson from "@contract/mock_investigation.json";
import type {
  ApproveResult,
  Complaint,
  Investigation,
  MemoryEntry,
} from "./types";

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
    due_in_working_days: 3,
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
    due_in_working_days: 8,
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
  },
];

const MOCK_MEMORY: MemoryEntry[] = [
  {
    id: "MEM-014",
    defect_type: "tombstoning",
    root_cause:
      "Reflow belt speed increase shortened time above liquidus on Line 1, reducing solder wetting and causing component tombstoning on 0402 capacitors.",
    parameter: "belt_speed_cm_min",
    line: "Line 1",
    capa_id: "CAPA-0098",
    lot_id: "L2389",
    investigation_id: "inv_2026_024",
    created: "2026-07-14",
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
  });
}
