import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getInvestigationReady, resolveApiUrl } from "../api/client";
import { useInvestigationStream } from "../api/useInvestigationStream";
import type { Investigation } from "../api/types";
import { BackNav } from "../components/BackNav";
import { CitationChip } from "../components/CitationChip";
import { ProvenanceTag } from "../components/ProvenanceTag";
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

  if (!inv) {
    return (
      <div className="flex flex-col gap-4">
        <BackNav investigationId={id} />
        <p className="text-sm opacity-60">Loading evidence…</p>
      </div>
    );
  }

  const hypothesisText = (hid: string) => inv.hypotheses.find((h) => h.id === hid)?.text ?? hid;
  const chartUrl = resolveApiUrl(inv.chart_url);

  return (
    <div className="flex flex-col gap-6">
      <BackNav investigationId={id} />
      <h1 className="text-lg font-semibold">Evidence</h1>

      <section>
        <h2 className="text-sm font-semibold opacity-80 mb-1">Reflow peak temperature, Line 2</h2>
        <p className="mb-2">
          <ProvenanceTag tone="computed">Computed from lot data</ProvenanceTag>
        </p>
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
        <h2 className="text-sm font-semibold opacity-80 mb-1">Hypothesis test results</h2>
        <p className="mb-2">
          <ProvenanceTag tone="computed">Computed from lot data — not AI</ProvenanceTag>
        </p>
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

      {inv.voice_note && (
        <section>
          <h2 className="text-sm font-semibold opacity-80 mb-1">Shift lead voice note</h2>
          <p className="mb-2">
            <ProvenanceTag tone="ai">
              AI — Gemini multimodal audio, heard in {inv.voice_note.language_name || "an unidentified language"}
            </ProvenanceTag>
          </p>
          <div className="card p-4 flex flex-col gap-3 text-sm">
            {inv.voice_note.lot_or_line && (
              <p>
                <span className="opacity-60">Referring to: </span>
                <span className="mono">{inv.voice_note.lot_or_line}</span>
                {inv.voice_note.low_confidence_fields.includes("lot_or_line") && (
                  <span className="ml-2 text-xs font-medium" style={{ color: "var(--amber)" }}>
                    unclear — confirm before relying on this
                  </span>
                )}
              </p>
            )}

            {inv.voice_note.observations.length > 0 && (
              <div>
                <p className="opacity-60 mb-1">Observations</p>
                <ul className="list-disc pl-5">
                  {inv.voice_note.observations.map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
                {inv.voice_note.low_confidence_fields.includes("observations") && (
                  <p className="text-xs mt-1" style={{ color: "var(--amber)" }}>
                    Flagged — not fully confident in this transcription.
                  </p>
                )}
              </div>
            )}

            {inv.voice_note.maintenance_mentions.length > 0 && (
              <div>
                <p className="opacity-60 mb-1">Maintenance mentioned</p>
                <ul className="list-disc pl-5">
                  {inv.voice_note.maintenance_mentions.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
                {inv.voice_note.low_confidence_fields.includes("maintenance_mentions") && (
                  <p className="text-xs mt-1" style={{ color: "var(--amber)" }}>
                    Flagged — not fully confident in this transcription.
                  </p>
                )}
              </div>
            )}

            <div>
              <p className="opacity-60 mb-1">
                Transcript{inv.voice_note.language_name ? ` (${inv.voice_note.language_name})` : ""}
              </p>
              <p className="italic">&ldquo;{inv.voice_note.transcript}&rdquo;</p>
            </div>

            {inv.voice_note.translation && inv.voice_note.translation !== inv.voice_note.transcript && (
              <div>
                <p className="opacity-60 mb-1">English translation</p>
                <p className="italic">&ldquo;{inv.voice_note.translation}&rdquo;</p>
              </div>
            )}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold opacity-80 mb-1">Citations</h2>
        <p className="mb-2">
          <ProvenanceTag tone="quoted">Quoted from the source documents</ProvenanceTag>
        </p>
        <div className="flex flex-wrap gap-2">
          {inv.citations.map((c, i) => (
            <CitationChip key={`${c.source}-${c.ref}-${i}`} citation={c} />
          ))}
        </div>
      </section>
    </div>
  );
}
