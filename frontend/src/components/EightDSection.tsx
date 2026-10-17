import { useRef } from "react";
import type { Citation } from "../api/types";
import { CitationChip } from "./CitationChip";
import { ProvenanceTag } from "./ProvenanceTag";

function autoGrow(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

/** One collapsible D1-D8 section: an auto-growing textarea the engineer can edit,
 * with its citations shown as chips so every claim stays traceable while editing. */
export function EightDSection({
  id,
  label,
  text,
  citations,
  onChange,
  defaultOpen = false,
}: {
  id: string;
  label: string;
  text: string;
  citations: Citation[];
  onChange: (text: string) => void;
  defaultOpen?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  return (
    <details className="card p-0 overflow-hidden" open={defaultOpen}>
      <summary className="tap-target flex items-center gap-2 px-4 cursor-pointer list-none font-semibold text-sm flex-wrap">
        <span className="mono text-xs opacity-60">{id}</span>
        {label}
        <span className="ml-auto font-normal">
          <ProvenanceTag tone="ai">AI-drafted · edit before approving</ProvenanceTag>
        </span>
      </summary>
      <div className="px-4 pb-4 flex flex-col gap-3">
        <label htmlFor={`${id}-text`} className="sr-only">
          {id}: {label}
        </label>
        <textarea
          id={`${id}-text`}
          ref={(el) => {
            ref.current = el;
            autoGrow(el);
          }}
          value={text}
          onChange={(e) => {
            onChange(e.target.value);
            autoGrow(e.target);
          }}
          rows={2}
          className="w-full resize-none rounded-lg border p-3 text-sm leading-relaxed bg-transparent"
          style={{ borderColor: "var(--line)" }}
        />
        {citations.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {citations.map((c, i) => (
              <CitationChip key={`${c.source}-${c.ref}-${i}`} citation={c} />
            ))}
          </div>
        )}
      </div>
    </details>
  );
}
