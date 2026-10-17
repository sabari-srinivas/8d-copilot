import type { Hypothesis, HypothesisResult } from "../api/types";
import { ProvenanceTag } from "./ProvenanceTag";
import { VerdictPill } from "./VerdictPill";

function formatPValue(p: number): string {
  if (p < 0.0001) return "< 0.0001";
  return `p = ${p.toFixed(4)}`;
}

/** One hypothesis, tested or still being tested. Rejected and inconclusive results
 * stay on screen exactly like supported ones — this card never disappears once it
 * has rendered, and callers must never filter the list before passing it in. */
export function HypothesisCard({
  hypothesis,
  result,
}: {
  hypothesis: Hypothesis;
  result?: HypothesisResult;
}) {
  return (
    <article
      className="card p-4 flex flex-col gap-2"
      aria-label={`Hypothesis ${hypothesis.id}: ${result ? result.verdict : "testing"}`}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-xs font-semibold uppercase tracking-wide opacity-60 mono">
          {hypothesis.id} · {hypothesis.category}
        </span>
        {result ? (
          <VerdictPill verdict={result.verdict} />
        ) : (
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
            style={{ background: "var(--line)" }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: "var(--ink)" }} aria-hidden="true" />
            Testing…
          </span>
        )}
      </div>

      <p className="text-sm leading-snug">{hypothesis.text}</p>
      <ProvenanceTag tone="ai">AI-proposed</ProvenanceTag>

      {hypothesis.parameter && (
        <p className="text-xs opacity-60">
          Parameter: <span className="mono">{hypothesis.parameter}</span>
          {hypothesis.event_wo_id ? <> · Event: <span className="mono">{hypothesis.event_wo_id}</span></> : null}
        </p>
      )}

      {result && (
        <ProvenanceTag tone="computed">
          Computed from lot data · {result.test}, {formatPValue(result.p_value)}
        </ProvenanceTag>
      )}

      {result && (
        <dl className="mt-1 grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs mono">
          <div>
            <dt className="opacity-60 font-sans text-[11px]">Test</dt>
            <dd>{result.test}</dd>
          </div>
          <div>
            <dt className="opacity-60 font-sans text-[11px]">p-value</dt>
            <dd>{formatPValue(result.p_value)}</dd>
          </div>
          <div>
            <dt className="opacity-60 font-sans text-[11px]">Effect</dt>
            <dd>{result.effect}</dd>
          </div>
          <div>
            <dt className="opacity-60 font-sans text-[11px]">n (defect vs good)</dt>
            <dd>{result.n_defect} vs {result.n_good}</dd>
          </div>
        </dl>
      )}
    </article>
  );
}
