import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import type { TravelerRow } from "../api/types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const SPEC_LOW = 235;
const SPEC_HIGH = 250;

/** Reads a colour token straight off the page at render time, so the chart — which
 * Chart.js draws on a <canvas>, outside the CSS cascade — still follows the same
 * CSS-variable tokens as everything else instead of a hardcoded hex fallback baked in
 * for one theme. Falls back only if the variable is somehow unset. */
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/** Client-rendered fallback for the reflow peak temperature chart, built from the
 * traveler rows already on the investigation — used when the backend-rendered
 * chart image (chart_url) can't be reached, e.g. in mock mode with no API running. */
export function TempChart({ rows, holdLots }: { rows: TravelerRow[]; holdLots: string[] }) {
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  const values = sorted.map((r) => r.reflow_peak_temp_c ?? 0);
  const isDefect = sorted.map((r) => holdLots.includes(r.lot_id));

  const red = cssVar("--red", "#a6281f");
  const green = cssVar("--green", "#1b5e3f");
  const ink = cssVar("--ink", "#16211c");
  const line = cssVar("--line", "#e2e8e4");
  const monoFont = { family: "Fira Code, ui-monospace, monospace" };

  const data: ChartData<"bar"> = {
    labels: sorted.map((r) => r.lot_id),
    datasets: [
      {
        label: "Reflow peak temperature (°C)",
        data: values,
        backgroundColor: isDefect.map((d) => (d ? red : green)),
        borderRadius: 3,
      },
    ],
  };

  const options: ChartOptions<"bar"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: monoFont,
        bodyFont: monoFont,
        callbacks: {
          label: (ctx) => `${ctx.label}: ${(ctx.parsed.y ?? 0).toFixed(1)} °C${
            isDefect[ctx.dataIndex] ? " (hold lot)" : ""
          }`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: ink, font: monoFont },
        grid: { color: line },
      },
      y: {
        title: { display: true, text: "°C", color: ink },
        ticks: { color: ink, font: monoFont },
        grid: { color: line },
        suggestedMin: Math.min(SPEC_LOW - 5, ...values),
        suggestedMax: Math.max(SPEC_HIGH + 5, ...values),
      },
    },
  };

  const caption =
    "Bar chart of reflow peak temperature in degrees Celsius per lot, Line 2. " +
    `Lots on hold (${holdLots.join(", ") || "none"}) are shown in red; other sampled lots in green. ` +
    `The qualified profile limit is ${SPEC_LOW}-${SPEC_HIGH} °C.`;

  return (
    <figure className="m-0">
      <div role="img" aria-label={caption} className="h-64">
        <Bar data={data} options={options} aria-hidden="true" />
      </div>
      <figcaption className="mt-2 text-xs opacity-60">{caption}</figcaption>
    </figure>
  );
}
