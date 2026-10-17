import { Quote } from "lucide-react";
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
        className="tap-target mono inline-flex items-center gap-1 rounded-md border px-2.5 text-xs font-medium transition-colors hover:bg-[var(--surface-hover)]"
        style={{ borderColor: "var(--line)" }}
      >
        <Quote size={11} aria-hidden="true" className="opacity-60 shrink-0" />
        {citation.label}
      </button>
      {open && <CitationSheet citation={citation} onClose={() => setOpen(false)} />}
    </>
  );
}
