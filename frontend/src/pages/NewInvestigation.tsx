import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createInvestigation, listComplaints } from "../api/client";
import type { Complaint } from "../api/types";

/** Route "/new" — upload the defect photo and (optionally) the lot traveler, confirm
 * the complaint text and lot, and start the investigation. */
export function NewInvestigation() {
  const [params] = useSearchParams();
  const complaintId = params.get("complaint") ?? "";
  const navigate = useNavigate();

  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [complaintText, setComplaintText] = useState("");
  const [lotId, setLotId] = useState("");
  const [imageName, setImageName] = useState("");
  const [travelerName, setTravelerName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!complaintId) return;
    listComplaints().then((list) => {
      const found = list.find((c) => c.complaint_id === complaintId) ?? null;
      setComplaint(found);
      if (found) {
        setComplaintText(found.text);
        setLotId(found.lot_id);
      }
    });
  }, [complaintId]);

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
      <h1 className="text-lg font-semibold mb-1">New investigation</h1>
      <p className="text-sm opacity-70 mb-6">
        {complaintId ? (
          <>
            For complaint <span className="mono">{complaintId}</span>
            {complaint ? ` · ${complaint.customer} · ${complaint.product}` : ""}
          </>
        ) : (
          "No complaint selected — fill in the details manually."
        )}
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
