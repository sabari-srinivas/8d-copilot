import type { ProposedAction } from "../api/types";

const KIND_LABEL: Record<ProposedAction["kind"], string> = {
  capa: "CAPA",
  hold: "Lot hold",
  work_order: "Work order",
  customer_reply: "Customer reply",
};

/** One of the four proposed actions (CAPA, hold, work order, customer reply), with
 * a switch to accept or reject it before approval. Accepted by default. */
export function ActionToggle({
  action,
  checked,
  onChange,
}: {
  action: ProposedAction;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="card p-3 flex items-center gap-3">
      <div className="min-w-0 flex-1">
        <span
          className="text-[11px] font-semibold uppercase tracking-wide opacity-60 rounded px-1.5 py-0.5 mr-2"
          style={{ background: "var(--line)" }}
        >
          {KIND_LABEL[action.kind]}
        </span>
        <p className="text-sm mt-1">{action.summary}</p>
      </div>
      <label className="tap-target flex items-center gap-2 shrink-0 text-xs font-medium cursor-pointer select-none">
        <span className="hidden sm:inline">{checked ? "Included" : "Excluded"}</span>
        <span className="relative inline-flex h-7 w-12 items-center rounded-full transition-colors" style={{ background: checked ? "var(--green)" : "var(--line)" }}>
          <input
            type="checkbox"
            className="absolute inset-0 opacity-0 cursor-pointer tap-target"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            aria-label={`${checked ? "Exclude" : "Include"} ${KIND_LABEL[action.kind]}: ${action.summary}`}
          />
          <span
            className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform"
            style={{ transform: checked ? "translateX(22px)" : "translateX(3px)" }}
            aria-hidden="true"
          />
        </span>
      </label>
    </div>
  );
}
