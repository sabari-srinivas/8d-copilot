import { useState } from "react";
import type { Defect } from "../api/types";

function humanize(s: string): string {
  const words = s.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The uploaded defect photo with the vision agent's bounding box drawn as a
 * positioned div from the 0-1 fractions in `defect.box`, plus the one-line chip
 * summarizing what was found (e.g. "Solder bridge · Major · 86%"). */
export function DefectPhoto({
  photoUrl,
  defect,
}: {
  photoUrl: string | null;
  defect: Defect | null;
}) {
  const [imgFailed, setImgFailed] = useState(false);
  const alt = defect
    ? `Defect photo: ${humanize(defect.type)}, ${defect.severity} severity. ${defect.visual_evidence}`
    : "Defect photo, not yet analyzed";

  const showImage = photoUrl && !imgFailed;

  return (
    <figure className="m-0">
      <div
        className="relative w-full aspect-[4/3] rounded-xl overflow-hidden border"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}
      >
        {showImage ? (
          <img
            src={photoUrl}
            alt={alt}
            className="w-full h-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div
            role="img"
            aria-label={alt}
            className="w-full h-full flex items-center justify-center text-xs text-center px-6 opacity-60"
          >
            Synthetic demo photo not available in this environment.
          </div>
        )}

        {defect && showImage && (
          <div
            className="absolute border-2 rounded-sm"
            style={{
              left: `${defect.box[0] * 100}%`,
              top: `${defect.box[1] * 100}%`,
              width: `${defect.box[2] * 100}%`,
              height: `${defect.box[3] * 100}%`,
              borderColor: "var(--red)",
              boxShadow: "0 0 0 1px rgba(255,255,255,0.6)",
            }}
            aria-hidden="true"
          />
        )}
      </div>

      {defect && (
        <figcaption className="mt-2 flex flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold text-white mono"
            style={{ background: "var(--ink)" }}
          >
            {humanize(defect.type)} · {humanize(defect.severity)} ·{" "}
            {Math.round(defect.confidence * 100)}%
          </span>
        </figcaption>
      )}
    </figure>
  );
}
