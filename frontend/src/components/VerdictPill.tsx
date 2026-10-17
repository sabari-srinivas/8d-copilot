import { AlertTriangle, Check, X } from "lucide-react";
import type { Verdict } from "../api/types";

// Carries the verdict as a WORD, not colour alone — must still read correctly in
// greyscale (PRD §13 accessibility). Colour is a reinforcement, never the only signal.
// `fg` is picked per-theme (--pill-fg-strong / --pill-fg-amber in index.css) so every
// fill clears 4.5:1 in BOTH light and dark — a plain white-on-amber or white-on-light
// fill does not (see visual-redesign-report.md for the measured ratios).
const STYLE: Record<Verdict, { bg: string; fg: string; label: string; Icon: typeof Check }> = {
  supported: { bg: "var(--green)", fg: "var(--pill-fg-strong)", label: "Supported", Icon: Check },
  rejected: { bg: "var(--grey)", fg: "var(--pill-fg-strong)", label: "Rejected", Icon: X },
  inconclusive: { bg: "var(--amber)", fg: "var(--pill-fg-amber)", label: "Inconclusive", Icon: AlertTriangle },
};

export function VerdictPill({ verdict }: { verdict: Verdict }) {
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
