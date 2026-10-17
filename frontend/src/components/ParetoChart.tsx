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
import type { DefectPareto } from "../api/types";
import { cssVar, monoFont } from "../lib/chartTheme";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

/** The defect Pareto: solder bridges vs every other defect type, descending. Red for
 * the known, root-caused defect; grey for the catch-all "other" bucket -- the same
 * supported/rejected colour convention VerdictPill already uses, not a new palette. */
export function ParetoChart({ data }: { data: DefectPareto }) {
  const ink = cssVar("--ink", "#16211c");
  const gridLine = cssVar("--line", "#e2e8e4");
  const red = cssVar("--red", "#a6281f");
  const grey = cssVar("--grey", "#6b7670");

  const entries = [
    { label: "Solder bridge", value: data.solder_bridge, color: red },
    { label: "Other", value: data.other, color: grey },
  ].sort((a, b) => b.value - a.value);
  const total = entries.reduce((s, e) => s + e.value, 0) || 1;

  const chartData: ChartData<"bar"> = {
    labels: entries.map((e) => e.label),
    datasets: [
      {
        label: "Defects",
        data: entries.map((e) => e.value),
        backgroundColor: entries.map((e) => e.color),
        borderRadius: 3,
        barThickness: 28,
      },
    ],
  };

  const options: ChartOptions<"bar"> = {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: monoFont,
        bodyFont: monoFont,
        callbacks: {
          label: (ctx) => `${ctx.label}: ${ctx.parsed.x} (${((Number(ctx.parsed.x) / total) * 100).toFixed(0)}%)`,
        },
      },
    },
    scales: {
      x: { ticks: { color: ink, font: monoFont }, grid: { color: gridLine } },
      y: { ticks: { color: ink, font: monoFont }, grid: { display: false } },
    },
  };

  const caption =
    `Horizontal bar chart (Pareto) of ${total} total defects: ` +
    entries.map((e) => `${e.label} ${e.value}`).join(", ") + ".";

  return (
    <figure className="m-0">
      <div role="img" aria-label={caption} className="h-36">
        <Bar data={chartData} options={options} aria-hidden="true" />
      </div>
      <figcaption className="mt-2 text-xs opacity-60">{caption}</figcaption>
    </figure>
  );
}
