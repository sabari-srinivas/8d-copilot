import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { prettySource } from "../api/capability";
import type { Citation } from "../api/types";
import { ProvenanceTag } from "./ProvenanceTag";

/** The quote behind a citation chip, with its source and reference. A simple,
 * accessible dialog: focus moves in on open, Escape and backdrop click close it. */
export function CitationSheet({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      style={{ background: "rgba(0,0,0,0.4)" }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="citation-sheet-title"
        className="card w-full sm:max-w-md p-5 rounded-b-none sm:rounded-b-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="citation-sheet-title" className="text-sm font-semibold">
            {citation.label}
          </h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="tap-target shrink-0 grid place-items-center rounded-full text-sm opacity-70 hover:opacity-100 transition-opacity"
            aria-label="Close citation"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        <p className="mt-3">
          <ProvenanceTag tone="quoted">Quoted from {prettySource(citation.source)}</ProvenanceTag>
        </p>
        <blockquote className="mt-1 text-sm leading-relaxed border-l-2 pl-3" style={{ borderColor: "var(--green)" }}>
          {citation.quote || "No quoted passage recorded for this citation."}
        </blockquote>
        <p className="mt-3 text-xs opacity-60 mono">
          {citation.source} · {citation.ref}
        </p>
      </div>
    </div>
  );
}
