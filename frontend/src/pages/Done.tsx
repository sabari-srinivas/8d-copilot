import { ArrowRight, CheckCircle2, Copy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getInvestigation } from "../api/client";
import type { ApproveResult, Investigation } from "../api/types";
import { BackNav } from "../components/BackNav";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { ProvenanceTag } from "../components/ProvenanceTag";

type DoneState = { result: ApproveResult; note: string } | undefined;

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card p-3 flex flex-col gap-1.5">
      <h2 className="stat-label">{title}</h2>
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

  // actions.py returns a null `replies` both when the approver excluded the customer
  // reply at review AND when the Gemini call that drafts it failed (e.g. a 429) --
  // the two cases are otherwise indistinguishable in the response. rejected_action_ids
  // is the only way to tell them apart: only call it "excluded" if the customer-reply
  // action's id is actually in that list. Defaults to "could not be completed" (not
  // "excluded") whenever that can't be proven -- e.g. `inv` hasn't loaded yet -- so a
  // judge watching a quota failure is never told the engineer chose to skip something
  // they did not.
  const customerReplyActionId = inv?.proposed_actions.find((a) => a.kind === "customer_reply")?.id;
  const replyWasExcluded =
    customerReplyActionId != null &&
    (state?.result.rejected_action_ids ?? []).includes(customerReplyActionId);

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
    <div className="flex flex-col gap-4 max-w-2xl">
      <Breadcrumbs
        items={[
          { label: "Complaints", to: "/complaints" },
          { label: `Investigation ${id ?? ""}`, to: `/inv/${id}` },
          { label: "Done" },
        ]}
      />
      <BackNav investigationId={id} />
      <div>
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <CheckCircle2 size={18} style={{ color: "var(--green)" }} aria-hidden="true" />
          8D approved by Priya R.
        </h1>
        <p className="text-sm opacity-70">
          Investigation <span className="mono">{id}</span>
          {confirmedCause && <> · confirmed cause: {confirmedCause}</>}
        </p>
      </div>

      {state?.result.capa_id && (
        // No dead ends: approval is the end of the investigation flow but not the end
        // of the lifecycle. This is the obvious, impossible-to-miss next step straight
        // to the CAPA record just created -- CapaCard's own `?highlight=` reads this
        // same id and rings the matching card so it is unmistakable in the list.
        <Link
          to={`/capa?highlight=${encodeURIComponent(state.result.capa_id)}`}
          className="tap-target inline-flex items-center justify-between gap-2 rounded-md px-4 text-sm font-semibold text-[var(--pill-fg-strong)] w-fit transition-opacity hover:opacity-90"
          style={{ background: "var(--green)" }}
        >
          Continue to CAPA {state.result.capa_id}
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      )}

      {!state && (
        <div className="card p-3 text-sm" role="status">
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
                <ProvenanceTag tone="ai">AI-drafted</ProvenanceTag>
                <div className="flex gap-1 w-fit rounded-md border p-1" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Reply language">
                  {(["ja", "en"] as const).map((l) => (
                    <button
                      key={l}
                      type="button"
                      role="tab"
                      aria-selected={lang === l}
                      onClick={() => setLang(l)}
                      className="tap-target rounded-md px-3 text-sm font-medium transition-colors"
                      style={{
                        background: lang === l ? "var(--green)" : "transparent",
                        color: lang === l ? "var(--pill-fg-strong)" : "inherit",
                      }}
                    >
                      {l === "ja" ? "日本語" : "English"}
                    </button>
                  ))}
                </div>
                <pre className="whitespace-pre-wrap text-sm rounded-md border p-3 mt-2" style={{ borderColor: "var(--line)" }}>
                  {state.result.replies[lang]}
                </pre>
                <button
                  type="button"
                  onClick={copyReply}
                  className="tap-target inline-flex items-center gap-1.5 rounded-md px-4 text-sm font-semibold w-fit border transition-colors hover:bg-[var(--surface-hover)]"
                  style={{ borderColor: "var(--line)" }}
                >
                  <Copy size={14} aria-hidden="true" />
                  {copied ? "Copied" : "Copy"}
                </button>
              </>
            ) : (
              <p className="text-sm opacity-60">
                {replyWasExcluded
                  ? "No customer reply was drafted (excluded at review)."
                  : "The customer reply could not be completed."}
              </p>
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
