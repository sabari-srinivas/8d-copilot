import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getInvestigationReady, resolveApiUrl } from "../api/client";
import { useInvestigationStream } from "../api/useInvestigationStream";
import type { Investigation } from "../api/types";
import { CitationChip } from "../components/CitationChip";
import { TempChart } from "../components/TempChart";

function formatPValue(p: number): string {
  if (p < 0.0001) return "< 0.0001";
  return p.toFixed(4);
}

/** Route "/inv/:id/evidence" — the numbers behind the draft: the reflow-temperature
 * chart, a full stats table per hypothesis, and every citation with its source quote. */
export function Evidence() {
  const { id } = useParams<{ id: string }>();
  // See Review.tsx: the GET can race the `draft_ready`/`insufficient_evidence` event
  // that's supposed to mean "the run is done" — fetch once the stream says the run
  // has left `running`, not unconditionally on mount.
  const stream = useInvestigationStream(id);
  const [inv, setInv] = useState<Investigation | null>(null);
  const [chartFailed, setChartFailed] = useState(false);

  useEffect(() => {
    if (!id || stream.status === "running") return;
    let cancelled = false;
    getInvestigationReady(id, (data) => data.status !== "running").then((data) => {
      if (!cancelled) setInv(data);
    });
    return () => {
      cancelled = true;
    };
  }, [id, stream.status]);

  if (!inv) return <p className="text-sm opacity-60">Loading evidence…</p>;

  const hypothesisText = (hid: string) => inv.hypotheses.find((h) => h.id === hid)?.text ?? hid;
  const chartUrl = resolveApiUrl(inv.chart_url);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg font-semibold">Evidence</h1>

      <section>
        <h2 className="text-sm font-semibold opacity-80 mb-2">Reflow peak temperature, Line 2</h2>
        {chartUrl && !chartFailed ? (
          <img
            src={chartUrl}
            alt="Chart comparing reflow peak temperature in defect lots versus good lots on Line 2, showing defect lots running hotter after work order WO-388."
            className="w-full rounded-xl border"
            style={{ borderColor: "var(--line)" }}
            onError={() => setChartFailed(true)}
          />
        ) : (
          <TempChart rows={inv.traveler_rows} holdLots={inv.hold_lots} />
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold opacity-80 mb-2">Hypothesis test results</h2>
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b" style={{ borderColor: "var(--line)" }}>
                <th className="p-3 font-medium">Hypothesis</th>
                <th className="p-3 font-medium">Test</th>
                <th className="p-3 font-medium mono">p-value</th>
                <th className="p-3 font-medium">Effect</th>
                <th className="p-3 font-medium mono">n (defect / good)</th>
              </tr>
            </thead>
            <tbody>
              {inv.results.map((r) => (
                <tr key={r.hypothesis_id} className="border-b last:border-0" style={{ borderColor: "var(--line)" }}>
                  <td className="p-3 align-top">
                    <span className="mono text-xs opacity-60">{r.hypothesis_id}</span>
                    <p className="max-w-xs">{hypothesisText(r.hypothesis_id)}</p>
                  </td>
                  <td className="p-3 align-top whitespace-nowrap">{r.test}</td>
                  <td className="p-3 align-top mono whitespace-nowrap">{formatPValue(r.p_value)}</td>
                  <td className="p-3 align-top mono whitespace-nowrap">{r.effect}</td>
                  <td className="p-3 align-top mono whitespace-nowrap">
                    {r.n_defect} / {r.n_good}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold opacity-80 mb-2">Citations</h2>
        <div className="flex flex-wrap gap-2">
          {inv.citations.map((c, i) => (
            <CitationChip key={`${c.source}-${c.ref}-${i}`} citation={c} />
          ))}
        </div>
      </section>
    </div>
  );
}
