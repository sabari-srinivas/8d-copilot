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

/** Client-rendered fallback for the reflow peak temperature chart, built from the
 * traveler rows already on the investigation — used when the backend-rendered
 * chart image (chart_url) can't be reached, e.g. in mock mode with no API running. */
export function TempChart({ rows, holdLots }: { rows: TravelerRow[]; holdLots: string[] }) {
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  const values = sorted.map((r) => r.reflow_peak_temp_c ?? 0);
  const isDefect = sorted.map((r) => holdLots.includes(r.lot_id));

  const data: ChartData<"bar"> = {
    labels: sorted.map((r) => r.lot_id),
    datasets: [
      {
        label: "Reflow peak temperature (°C)",
        data: values,
        backgroundColor: isDefect.map((d) =>
          d ? "rgba(166, 40, 31, 0.75)" : "rgba(27, 94, 63, 0.6)",
        ),
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
        callbacks: {
          label: (ctx) => `${ctx.label}: ${(ctx.parsed.y ?? 0).toFixed(1)} °C${
            isDefect[ctx.dataIndex] ? " (hold lot)" : ""
          }`,
        },
      },
    },
    scales: {
      y: {
        title: { display: true, text: "°C" },
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
