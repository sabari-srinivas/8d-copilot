/** Reads a colour token straight off the page at render time, so a chart drawn on a
 * <canvas> -- outside the CSS cascade -- still follows the same CSS-variable tokens as
 * everything else, in both light and dark, instead of a hardcoded hex baked in for one
 * theme. Same pattern as components/TempChart.tsx's own `cssVar`, duplicated here
 * rather than imported from it: TempChart belongs to the investigation flow, which
 * must stay completely untouched by this dashboard/CAPA/plant work. */
export function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export const monoFont = { family: "Fira Code, ui-monospace, monospace" };
