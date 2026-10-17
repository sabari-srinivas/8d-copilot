import type { ReactNode } from "react";
import type { Provenance } from "../api/capability";

const TONE_COLOR: Record<Provenance, string> = {
  ai: "var(--ink)",
  computed: "var(--green-ink)",
  quoted: "var(--ink)",
};

/**
 * Small, secondary provenance metadata — never a badge competing with the content it
 * labels. Carries this product's central claim in writing, element by element
 * (CHANGE_REQUESTS.md #2): the model proposes (tone "ai"), deterministic code decides
 * (tone "computed"), and a quote is lifted verbatim (tone "quoted"). A verdict, a
 * p-value or an effect size must never be passed tone="ai" — that would say the model
 * decided it, which is exactly the claim this product exists to refute.
 *
 * Text only, no colour-only signal: the tone colour is a reinforcement (readable in
 * greyscale as plain, slightly muted text), never the only thing distinguishing one
 * label from another — the words themselves always differ.
 */
export function ProvenanceTag({ tone, children }: { tone: Provenance; children: ReactNode }) {
  return (
    <span className="text-[11px] font-medium opacity-70" style={{ color: TONE_COLOR[tone] }}>
      {children}
    </span>
  );
}
