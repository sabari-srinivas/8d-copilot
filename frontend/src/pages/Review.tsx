import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { approve, getInvestigation } from "../api/client";
import type { EightD, Investigation } from "../api/types";
import { ActionToggle } from "../components/ActionToggle";
import { EightDSection } from "../components/EightDSection";

const SECTIONS: Array<{ id: keyof EightD; label: string }> = [
  { id: "D1", label: "Team" },
  { id: "D2", label: "Problem description" },
  { id: "D3", label: "Interim containment actions" },
  { id: "D4", label: "Root cause" },
  { id: "D5", label: "Permanent corrective action" },
  { id: "D6", label: "Implementation & validation" },
  { id: "D7", label: "Prevent recurrence" },
  { id: "D8", label: "Team recognition & closure" },
];

/** Route "/inv/:id/review" — the human approval gate. Every D-section is editable,
 * every claim stays cited, every action can be excluded. When the draft doesn't have
 * enough data, Approve is hidden outright — never shown disabled. */
export function Review() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [inv, setInv] = useState<Investigation | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getInvestigation(id).then((data) => {
      setInv(data);
      if (data.eight_d) {
        const initial: Record<string, string> = {};
        for (const s of SECTIONS) initial[s.id] = data.eight_d[s.id].text;
        setEdits(initial);
      }
    });
  }, [id]);

  const confirmedCause = useMemo(() => {
    if (!inv) return "";
    const supported = new Set(
      inv.results.filter((r) => r.verdict === "supported").map((r) => r.hypothesis_id),
    );
    return inv.hypotheses.find((h) => supported.has(h.id))?.text ?? "";
  }, [inv]);

  if (!inv) return <p className="text-sm opacity-60">Loading draft…</p>;

  const insufficientEvidence = inv.status === "insufficient_evidence";

  function toggleAction(actionId: string, checked: boolean) {
    setRejected((prev) => {
      const next = new Set(prev);
      if (checked) next.delete(actionId);
      else next.add(actionId);
      return next;
    });
  }

  async function onApprove() {
    if (!id) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await approve(id, {
        approver: "Priya R.",
        edits,
        rejected_action_ids: [...rejected],
        note,
      });
      navigate(`/inv/${id}/done`, { state: { result, note } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve the 8D.");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div>
        <h1 className="text-lg font-semibold">Review 8D</h1>
        <p className="text-sm opacity-70">
          Investigation <span className="mono">{id}</span>
          {confirmedCause && <> · confirmed cause: {confirmedCause}</>}
        </p>
      </div>

      {insufficientEvidence && (
        <div className="card p-4 flex flex-col gap-2" style={{ borderColor: "var(--amber)" }} role="alert">
          <p className="text-sm font-semibold" style={{ color: "var(--amber)" }}>
            This draft needs more data before it can be approved
          </p>
          {inv.missing_data.length > 0 ? (
            <ul className="text-sm list-disc pl-5">
              {inv.missing_data.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm opacity-80">No further detail was recorded about what's missing.</p>
          )}
        </div>
      )}

      {inv.eight_d && (
        <div className="flex flex-col gap-3">
          {SECTIONS.map((s, i) => (
            <EightDSection
              key={s.id}
              id={s.id}
              label={s.label}
              text={edits[s.id] ?? inv.eight_d![s.id].text}
              citations={inv.eight_d![s.id].citations}
              onChange={(text) => setEdits((prev) => ({ ...prev, [s.id]: text }))}
              defaultOpen={i < 2}
            />
          ))}
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold mb-2">Proposed actions</h2>
        <div className="flex flex-col gap-2">
          {inv.proposed_actions.map((a) => (
            <ActionToggle
              key={a.id}
              action={a}
              checked={!rejected.has(a.id)}
              onChange={(checked) => toggleAction(a.id, checked)}
            />
          ))}
        </div>
      </div>

      <div>
        <label htmlFor="note" className="block text-sm font-medium mb-1">
          Note <span className="font-normal opacity-60">— optional, goes on the approval record</span>
        </label>
        <textarea
          id="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          className="w-full resize-y rounded-lg border p-3 text-sm bg-transparent"
          style={{ borderColor: "var(--line)" }}
        />
      </div>

      {error && (
        <p role="alert" className="text-sm" style={{ color: "var(--red)" }}>
          {error}
        </p>
      )}

      {!insufficientEvidence && (
        <button
          type="button"
          onClick={onApprove}
          disabled={submitting}
          className="tap-target rounded-lg px-5 text-sm font-semibold text-white disabled:opacity-60 w-fit"
          style={{ background: "var(--green)" }}
        >
          {submitting ? "Approving…" : "Approve 8D"}
        </button>
      )}
    </div>
  );
}
