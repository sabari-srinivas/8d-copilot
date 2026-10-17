import { AlertTriangle, Check, HelpCircle, X } from "lucide-react";
import type { CapaVerdict } from "../api/types";

// Same convention as VerdictPill (hypothesis verdicts): the word is always present,
// colour only reinforces it -- must still read correctly in greyscale. worked=green
// (supported), never_worked=red (a confirmed failure, stronger than the grey
// "rejected" hypothesis verdict since this is a CAPA that was signed off and didn't
// work), regressed=amber (it worked, then stopped -- a warning), insufficient_data=grey
// (no claim made either way).
const STYLE: Record<CapaVerdict, { bg: string; fg: string; label: string; Icon: typeof Check }> = {
  worked: { bg: "var(--green)", fg: "var(--pill-fg-strong)", label: "Worked", Icon: Check },
  never_worked: { bg: "var(--red)", fg: "var(--pill-fg-strong)", label: "Never worked", Icon: X },
  regressed: { bg: "var(--amber)", fg: "var(--pill-fg-amber)", label: "Regressed", Icon: AlertTriangle },
  insufficient_data: { bg: "var(--grey)", fg: "var(--pill-fg-strong)", label: "Insufficient data", Icon: HelpCircle },
};

export function CapaVerdictPill({ verdict }: { verdict: CapaVerdict }) {
  const { bg, fg, label, Icon } = STYLE[verdict];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
      style={{ background: bg, color: fg }}
    >
      <Icon size={12} strokeWidth={3} aria-hidden="true" />
      {label}
    </span>
  );
}
