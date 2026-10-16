import type { Verdict } from "../api/types";

// Carries the verdict as a WORD, not colour alone — must still read correctly in
// greyscale (PRD §13 accessibility). Colour is a reinforcement, never the only signal.
const STYLE: Record<Verdict, { bg: string; label: string }> = {
  supported: { bg: "var(--green)", label: "Supported" },
  rejected: { bg: "var(--grey)", label: "Rejected" },
  inconclusive: { bg: "var(--amber)", label: "Inconclusive" },
};

export function VerdictPill({ verdict }: { verdict: Verdict }) {
  const s = STYLE[verdict];
  return (
    <span
      className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold text-white whitespace-nowrap"
      style={{ background: s.bg }}
    >
      {s.label}
    </span>
  );
}
