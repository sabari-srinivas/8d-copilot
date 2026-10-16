import { useState } from "react";
import type { Citation } from "../api/types";
import { CitationSheet } from "./CitationSheet";

/** A small inline reference ("PFMEA row 14") that opens the CitationSheet with the
 * full quote on demand — keeps 8D text scannable while every claim stays sourced. */
export function CitationChip({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="tap-target inline-flex items-center rounded-full border px-2.5 text-xs font-medium hover:bg-[var(--line)]"
        style={{ borderColor: "var(--line)" }}
      >
        {citation.label}
      </button>
      {open && <CitationSheet citation={citation} onClose={() => setOpen(false)} />}
    </>
  );
}
