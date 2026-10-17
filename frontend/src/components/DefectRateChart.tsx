import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartData,
  type ChartOptions,
  type Plugin,
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { DefectRateByLine } from "../api/types";
import { cssVar, monoFont } from "../lib/chartTheme";

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend);

/** The dashboard's hero chart (PRD: "the most persuasive image in the product") --
 * defect rate by date, Line 1 vs Line 2, with a dashed marker at the work order
 * (WO-388) after which Line 2's rate climbed. The two lines are plotted against a
 * shared, merged date axis (spanGaps bridges the days a given line had no lot) so the
 * drift is visible as a widening gap between two curves, not two unrelated series. */
export function DefectRateChart({ data }: { data: DefectRateByLine }) {
  const dates = Array.from(new Set([...data.line1, ...data.line2].map((p) => p.date))).sort();
  const byDate = (points: DefectRateByLine["line1"]) => {
    const map = new Map(points.map((p) => [p.date, p.rate_pct]));
    return dates.map((d) => map.get(d) ?? null);
  };

  const green = cssVar("--green", "#1b5e3f");
  const red = cssVar("--red", "#a6281f");
  const ink = cssVar("--ink", "#16211c");
  const gridLine = cssVar("--line", "#e2e8e4");
  const amber = cssVar("--amber", "#b7791f");
  const amberInk = cssVar("--amber-ink", "#855a10");

  const markerIndex = dates.findIndex((d) => d >= data.marker_date);

  const markerPlugin: Plugin<"line"> = {
    id: "wo388Marker",
    afterDraw(chart) {
      if (markerIndex < 0) return;
      const xScale = chart.scales.x;
      const { ctx, chartArea } = chart;
      const x = xScale.getPixelForValue(markerIndex);
      ctx.save();
      ctx.strokeStyle = amber;
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = amberInk;
      ctx.font = `600 11px ${monoFont.family}`;
      ctx.textAlign = "left";
      ctx.fillText(data.marker_label, x + 4, chartArea.top + 12);
      ctx.restore();
    },
  };

  const chartData: ChartData<"line"> = {
    labels: dates,
    datasets: [
      {
        label: `Line 1 (avg ${data.line1_avg_pct.toFixed(2)}%)`,
        data: byDate(data.line1),
        borderColor: green,
        backgroundColor: green,
        spanGaps: true,
        tension: 0.15,
        pointRadius: 2,
        borderWidth: 2,
      },
      {
        label: `Line 2 (avg ${data.line2_avg_pct.toFixed(2)}%)`,
        data: byDate(data.line2),
        borderColor: red,
        backgroundColor: red,
        spanGaps: true,
        tension: 0.15,
        pointRadius: 2,
        borderWidth: 2,
      },
    ],
  };

  const options: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "top", align: "end", labels: { color: ink, font: monoFont, usePointStyle: true, boxWidth: 8 } },
      tooltip: {
        titleFont: monoFont,
        bodyFont: monoFont,
        callbacks: { label: (ctx) => `${ctx.dataset.label}: ${(ctx.parsed.y ?? 0).toFixed(2)}%` },
      },
    },
    scales: {
      x: { ticks: { color: ink, font: monoFont, maxTicksLimit: 8 }, grid: { color: gridLine } },
      y: {
        title: { display: true, text: "Defect rate (%)", color: ink },
        ticks: { color: ink, font: monoFont },
        grid: { color: gridLine },
        beginAtZero: true,
      },
    },
  };

  const caption =
    `Line chart of solder-bridge defect rate by date: Line 1 in green, averaging ${data.line1_avg_pct.toFixed(2)}%; ` +
    `Line 2 in red, averaging ${data.line2_avg_pct.toFixed(2)}%. A marker at ${data.marker_label} ` +
    `(${data.marker_date}) shows the work order after which Line 2's rate climbed well above Line 1's.`;

  return (
    <figure className="m-0">
      <div role="img" aria-label={caption} className="h-72">
        <Line data={chartData} options={options} plugins={[markerPlugin]} aria-hidden="true" />
      </div>
      <figcaption className="mt-2 text-xs opacity-60">{caption}</figcaption>
    </figure>
  );
}
