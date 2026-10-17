import { Calculator, Quote, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import type { Provenance } from "../api/capability";

const TONE_COLOR: Record<Provenance, string> = {
  ai: "var(--ink)",
  computed: "var(--green-ink)",
  quoted: "var(--ink)",
};

// A small icon reinforces the distinction at a glance in a dense trace — never the
// only signal, the word is always printed right after it (see the component doc
// below). ai = a Gemini/embedding call proposed this, computed = deterministic code
// decided it, quoted = text lifted verbatim.
const TONE_ICON: Record<Provenance, typeof Sparkles> = {
  ai: Sparkles,
  computed: Calculator,
  quoted: Quote,
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
  const Icon = TONE_ICON[tone];
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-medium opacity-70"
      style={{ color: TONE_COLOR[tone] }}
    >
      <Icon size={11} strokeWidth={2} aria-hidden="true" className="shrink-0" />
      {children}
    </span>
  );
}
