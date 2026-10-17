import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { createInvestigation, listComplaints } from "../api/client";
import type { Complaint } from "../api/types";

/** Previous/next among the OPEN complaints, in the same due-date order the inbox shows
 * (CR #8) — lets Priya move to another complaint without detouring back through the
 * inbox each time. `null` when there is nowhere to go (only/first/last complaint). */
function AdjacentComplaintNav({
  complaints,
  currentId,
}: {
  complaints: Complaint[];
  currentId: string;
}) {
  const open = complaints
    .filter((c) => c.status === "open")
    .sort((a, b) => (a.due_in_working_days ?? Infinity) - (b.due_in_working_days ?? Infinity));
  const index = open.findIndex((c) => c.complaint_id === currentId);
  if (index === -1 || open.length < 2) return null;
  const prev = open[index - 1];
  const next = open[index + 1];

  return (
    <nav aria-label="Other complaints" className="flex items-center gap-3 text-sm mb-4">
      {prev ? (
        <Link
          to={`/new?complaint=${encodeURIComponent(prev.complaint_id)}`}
          className="tap-target inline-flex items-center gap-1 font-medium underline"
          style={{ color: "var(--green)" }}
        >
          ← {prev.customer}
        </Link>
      ) : (
        <span />
      )}
      <span className="opacity-40 mono text-xs ml-auto">
        {index + 1} of {open.length}
      </span>
      {next && (
        <Link
          to={`/new?complaint=${encodeURIComponent(next.complaint_id)}`}
          className="tap-target inline-flex items-center gap-1 font-medium underline"
          style={{ color: "var(--green)" }}
        >
          {next.customer} →
        </Link>
      )}
    </nav>
  );
}

/** Route "/new" — upload the defect photo and (optionally) the lot traveler, confirm
 * the complaint text and lot, and start the investigation.
 *
 * CR #1: this screen only makes sense FOR a complaint — an investigation with no
 * complaint has no customer, no product and no due date, so it is not reachable with
 * nothing selected; a direct hit with no `?complaint=` redirects to the inbox. */
export function NewInvestigation() {
  const [params] = useSearchParams();
  const complaintId = params.get("complaint") ?? "";
  const navigate = useNavigate();

  const [complaints, setComplaints] = useState<Complaint[] | null>(null);
  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [complaintText, setComplaintText] = useState("");
  const [lotId, setLotId] = useState("");
  const [imageName, setImageName] = useState("");
  const [travelerName, setTravelerName] = useState("");
  const [voiceNoteName, setVoiceNoteName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!complaintId) return;
    listComplaints().then((list) => {
      setComplaints(list);
      const found = list.find((c) => c.complaint_id === complaintId) ?? null;
      setComplaint(found);
      setNotFound(!found);
      if (found) {
        setComplaintText(found.text);
        setLotId(found.lot_id);
      }
    });
  }, [complaintId]);

  if (!complaintId || notFound) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = formRef.current;
    if (!form) return;
    const data = new FormData(form);
    data.set("complaint_id", complaintId);
    data.set("complaint_text", complaintText);
    data.set("lot_id", lotId);

    setSubmitting(true);
    try {
      const result = await createInvestigation(data);
      navigate(`/inv/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the investigation.");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      {complaints && <AdjacentComplaintNav complaints={complaints} currentId={complaintId} />}

      <h1 className="text-lg font-semibold mb-1">
        {complaint ? `${complaint.customer} · ${complaint.product}` : "Loading complaint…"}
      </h1>
      <p className="text-sm opacity-70 mb-1">
        Complaint <span className="mono">{complaintId}</span>
        {complaint ? ` · lot ${complaint.lot_id}` : ""}
      </p>
      {complaint?.is_rejection && (
        <p
          className="text-sm rounded-lg border px-3 py-2 mb-4"
          style={{ borderColor: "var(--red)", color: "var(--red)" }}
        >
          This is a customer rejection of an 8D already submitted. The agent will revise
          the rejected sections, not start a fresh investigation.
          {complaint.objection && <> Objection: &ldquo;{complaint.objection}&rdquo;</>}
        </p>
      )}
      <p className="text-sm opacity-70 mb-6">
        Photograph the returned board and confirm the lot before starting the
        investigation.
      </p>

      <form ref={formRef} onSubmit={onSubmit} className="flex flex-col gap-5">
        <div>
          <label htmlFor="image" className="block text-sm font-medium mb-1">
            Defect photo
          </label>
          <input
            id="image"
            name="image"
            type="file"
            accept="image/*"
            capture="environment"
            required
            onChange={(e) => setImageName(e.target.files?.[0]?.name ?? "")}
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-white file:bg-[var(--green)]"
            style={{ borderColor: "var(--line)" }}
          />
          <p className="text-xs opacity-60 mt-1" aria-live="polite">
            {imageName ? `Selected: ${imageName}` : "Opens the camera on a phone."}
          </p>
        </div>

        <div>
          <label htmlFor="complaint_text" className="block text-sm font-medium mb-1">
            Complaint text
          </label>
          <textarea
            id="complaint_text"
            value={complaintText}
            onChange={(e) => setComplaintText(e.target.value)}
            rows={4}
            className="w-full resize-y rounded-lg border p-3 text-sm bg-transparent"
            style={{ borderColor: "var(--line)" }}
          />
        </div>

        <div>
          <label htmlFor="lot_id" className="block text-sm font-medium mb-1">
            Lot ID
          </label>
          <input
            id="lot_id"
            value={lotId}
            onChange={(e) => setLotId(e.target.value)}
            required
            className="tap-target mono w-full rounded-lg border px-3 text-sm bg-transparent"
            style={{ borderColor: "var(--line)" }}
          />
        </div>

        <div>
          <label htmlFor="traveler" className="block text-sm font-medium mb-1">
            Lot traveler (.xlsx) <span className="font-normal opacity-60">— optional</span>
          </label>
          <input
            id="traveler"
            name="traveler"
            type="file"
            accept=".xlsx"
            onChange={(e) => setTravelerName(e.target.files?.[0]?.name ?? "")}
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-white file:bg-[var(--green)]"
            style={{ borderColor: "var(--line)" }}
          />
          {travelerName && <p className="text-xs opacity-60 mt-1">Selected: {travelerName}</p>}
        </div>

        <div>
          <label htmlFor="voice_note" className="block text-sm font-medium mb-1">
            Shift lead voice note <span className="font-normal opacity-60">— optional</span>
          </label>
          <input
            id="voice_note"
            name="voice_note"
            type="file"
            accept="audio/*"
            onChange={(e) => setVoiceNoteName(e.target.files?.[0]?.name ?? "")}
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-white file:bg-[var(--green)]"
            style={{ borderColor: "var(--line)" }}
          />
          <p className="text-xs opacity-60 mt-1" aria-live="polite">
            {voiceNoteName
              ? `Selected: ${voiceNoteName}`
              : "A recorded remark from the floor — Gemini reads it directly, in English, Tamil or Hindi."}
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="tap-target rounded-lg px-5 text-sm font-semibold text-white disabled:opacity-60"
          style={{ background: "var(--green)" }}
        >
          {submitting ? "Starting…" : "Start investigation"}
        </button>
      </form>
    </div>
  );
}
