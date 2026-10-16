import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { getInvestigation } from "../api/client";
import type { ApproveResult, Investigation } from "../api/types";

type DoneState = { result: ApproveResult; note: string } | undefined;

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card p-4 flex flex-col gap-2">
      <h2 className="text-sm font-semibold opacity-80">{title}</h2>
      {children}
    </section>
  );
}

/** Route "/inv/:id/done" — the end of the demo: CAPA, hold, work order and the
 * bilingual customer reply, plus confirmation that the cause was saved to memory. */
export function Done() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as DoneState;

  const [inv, setInv] = useState<Investigation | null>(null);
  const [lang, setLang] = useState<"ja" | "en">("ja");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) return;
    getInvestigation(id).then(setInv);
  }, [id]);

  const confirmedCause = useMemo(() => {
    if (!inv) return "";
    const supported = new Set(
      inv.results.filter((r) => r.verdict === "supported").map((r) => r.hypothesis_id),
    );
    return inv.hypotheses.find((h) => supported.has(h.id))?.text ?? "";
  }, [inv]);

  const workOrderSummary = inv?.proposed_actions.find((a) => a.kind === "work_order")?.summary;

  async function copyReply() {
    const text = state?.result.replies?.[lang] ?? "";
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-col gap-5 max-w-2xl">
      <div>
        <h1 className="text-lg font-semibold">8D approved by Priya R.</h1>
        <p className="text-sm opacity-70">
          Investigation <span className="mono">{id}</span>
          {confirmedCause && <> · confirmed cause: {confirmedCause}</>}
        </p>
      </div>

      {!state && (
        <div className="card p-4 text-sm" role="status">
          This page was opened directly, so the records created at approval time aren't
          available here — they're only returned once, by the approval call itself. The
          investigation's own status below still reflects the approval.
          {inv && <p className="mt-1 mono text-xs opacity-60">status: {inv.status}</p>}
        </div>
      )}

      {state && (
        <>
          <Card title="CAPA">
            {state.result.capa_id ? (
              <p className="text-sm">
                <span className="mono font-semibold">{state.result.capa_id}</span> opened for
                this investigation's confirmed root cause.
              </p>
            ) : (
              <p className="text-sm opacity-60">No CAPA was raised (excluded at review).</p>
            )}
          </Card>

          <Card title="Lot hold">
            {state.result.hold_id ? (
              <>
                <p className="text-sm">
                  <span className="mono font-semibold">{state.result.hold_id}</span> placed on:
                </p>
                <ul className="flex flex-wrap gap-2 mt-1">
                  {(inv?.hold_lots ?? []).map((lot) => (
                    <li key={lot} className="mono text-xs rounded-full px-2.5 py-1" style={{ background: "var(--line)" }}>
                      {lot}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="text-sm opacity-60">No lot hold was raised (excluded at review).</p>
            )}
          </Card>

          <Card title="Work order">
            {state.result.work_order_id ? (
              <p className="text-sm">
                <span className="mono font-semibold">{state.result.work_order_id}</span>
                {workOrderSummary ? ` — ${workOrderSummary}` : ""}
              </p>
            ) : (
              <p className="text-sm opacity-60">No work order was raised (excluded at review).</p>
            )}
          </Card>

          <Card title="Customer reply">
            {state.result.replies ? (
              <>
                <div className="flex gap-1 w-fit rounded-lg border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Reply language">
                  {(["ja", "en"] as const).map((l) => (
                    <button
                      key={l}
                      type="button"
                      role="tab"
                      aria-selected={lang === l}
                      onClick={() => setLang(l)}
                      className="tap-target rounded-md px-3 text-sm font-medium"
                      style={{
                        background: lang === l ? "var(--green)" : "transparent",
                        color: lang === l ? "white" : "inherit",
                      }}
                    >
                      {l === "ja" ? "日本語" : "English"}
                    </button>
                  ))}
                </div>
                <pre className="whitespace-pre-wrap text-sm rounded-lg border p-3 mt-2" style={{ borderColor: "var(--line)" }}>
                  {state.result.replies[lang]}
                </pre>
                <button
                  type="button"
                  onClick={copyReply}
                  className="tap-target rounded-lg px-4 text-sm font-semibold w-fit border"
                  style={{ borderColor: "var(--line)" }}
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </>
            ) : (
              <p className="text-sm opacity-60">No customer reply was drafted (excluded at review).</p>
            )}
          </Card>

          <Card title="Saved to quality memory">
            {state.result.memory_id ? (
              <p className="text-sm">
                <span className="mono font-semibold">{state.result.memory_id}</span> —{" "}
                {confirmedCause || "confirmed cause recorded"}
              </p>
            ) : (
              <p className="text-sm opacity-60">No confirmed cause was saved to memory.</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
