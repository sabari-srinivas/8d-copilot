import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { createInvestigation, listComplaints } from "../api/client";
import { plainName } from "../api/display";
import type { Complaint } from "../api/types";
import { VoiceRecorder, canRecordAudio } from "../components/VoiceRecorder";

// Read once at module load rather than per render: whether this browser can reach a
// microphone cannot change while the page is open, and calling it in the body would make
// the branch below re-evaluate on every keystroke in the complaint text.
const micAvailable = canRecordAudio();

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
    <nav
      aria-label="Other complaints"
      className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm mb-4"
    >
      {prev ? (
        <Link
          to={`/new?complaint=${encodeURIComponent(prev.complaint_id)}`}
          className="tap-target inline-flex items-center gap-1 font-medium underline shrink-0 whitespace-nowrap"
          style={{ color: "var(--green)" }}
        >
          <ArrowLeft size={14} aria-hidden="true" /> {plainName(prev.customer)}
        </Link>
      ) : (
        <span />
      )}
      <span className="opacity-40 mono text-xs shrink-0 order-first basis-full text-center sm:order-none sm:basis-auto sm:text-left">
        {index + 1} of {open.length}
      </span>
      {next && (
        <Link
          to={`/new?complaint=${encodeURIComponent(next.complaint_id)}`}
          className="tap-target inline-flex items-center gap-1 font-medium underline shrink-0 whitespace-nowrap"
          style={{ color: "var(--green)" }}
        >
          {plainName(next.customer)} <ArrowRight size={14} aria-hidden="true" />
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
  // CR #15: a blob recorded from the microphone, which lives outside the form element
  // (no file input holds it) and so has to be appended to the FormData by hand.
  const [recordedAudio, setRecordedAudio] = useState<{ blob: Blob; name: string } | null>(
    null,
  );
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
    // "/" is the dashboard now, not the complaint list -- redirect to the screen
    // that actually lets Priya pick a complaint (CR #1's point still holds: /new is
    // not a destination reachable with nothing selected).
    return <Navigate to="/complaints" replace />;
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
    // Posted under the same field name the file input used, so the endpoint sees no
    // difference between a recording and a chosen file (CR #15).
    if (recordedAudio) data.set("voice_note", recordedAudio.blob, recordedAudio.name);

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
        {complaint ? `${plainName(complaint.customer)} · ${complaint.product}` : "Loading complaint…"}
      </h1>
      <p className="text-sm opacity-70 mb-1">
        Complaint <span className="mono">{complaintId}</span>
        {complaint ? <> · lot <span className="mono">{complaint.lot_id}</span></> : ""}
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
      <p className="text-sm opacity-70 mb-5">
        Photograph the returned board and confirm the lot before starting the
        investigation.
      </p>

      <form ref={formRef} onSubmit={onSubmit} className="flex flex-col gap-4">
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
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-[var(--pill-fg-strong)] file:bg-[var(--green)]"
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
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-[var(--pill-fg-strong)] file:bg-[var(--green)]"
            style={{ borderColor: "var(--line)" }}
          />
          {travelerName && <p className="text-xs opacity-60 mt-1">Selected: {travelerName}</p>}
        </div>

        <div>
          <span id="voice_note_label" className="block text-sm font-medium mb-1">
            Shift lead voice note <span className="font-normal opacity-60">— optional</span>
          </span>
          <p className="text-xs opacity-60 mb-2">
            Speak a remark from the floor — Gemini reads the audio directly, in English,
            Tamil or Hindi.
          </p>
          {micAvailable ? (
            // CR #15: live capture, not a file picker. The blob never touches the form
            // element, so `new FormData(form)` cannot see it — it is appended by hand in
            // onSubmit from `recordedAudio` below.
            <VoiceRecorder onAudioChange={(blob, name) => setRecordedAudio(blob && { blob, name })} />
          ) : (
            // A browser with no MediaRecorder, or an insecure origin where
            // `navigator.mediaDevices` is undefined. The feature still works, it just
            // needs a file. This branch keeps the original `name="voice_note"` input, so
            // the form posts it the way it always did.
            <>
              <input
                id="voice_note"
                name="voice_note"
                type="file"
                accept="audio/*"
                aria-labelledby="voice_note_label"
                onChange={(e) => setVoiceNoteName(e.target.files?.[0]?.name ?? "")}
                className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-[var(--pill-fg-strong)] file:bg-[var(--green)]"
                style={{ borderColor: "var(--line)" }}
              />
              <p className="text-xs opacity-60 mt-1" aria-live="polite">
                {voiceNoteName
                  ? `Selected: ${voiceNoteName}`
                  : "This browser cannot record audio, so choose a file instead."}
              </p>
            </>
          )}
        </div>

        {error && (
          <p role="alert" className="text-sm" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="tap-target rounded-lg px-5 text-sm font-semibold text-[var(--pill-fg-strong)] disabled:opacity-60"
          style={{ background: "var(--green)" }}
        >
          {submitting ? "Starting…" : "Start investigation"}
        </button>
      </form>
    </div>
  );
}
