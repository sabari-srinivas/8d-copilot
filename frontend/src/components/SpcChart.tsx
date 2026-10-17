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
  type ScriptableLineSegmentContext,
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { SpcReflowPeak } from "../api/types";
import { cssVar, monoFont } from "../lib/chartTheme";

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend);

/** SPC-style control chart: reflow peak temperature across every lot, with the 250 °C
 * control limit drawn as a dashed reference line. Points/segments above the limit are
 * red, matching the hold-lot convention components/TempChart.tsx already uses on the
 * investigation evidence screen. */
export function SpcChart({ data }: { data: SpcReflowPeak }) {
  const ink = cssVar("--ink", "#16211c");
  const gridLine = cssVar("--line", "#e2e8e4");
  const green = cssVar("--green", "#1b5e3f");
  const red = cssVar("--red", "#a6281f");
  const amber = cssVar("--amber", "#b7791f");
  const amberInk = cssVar("--amber-ink", "#855a10");

  const points = data.points;
  const overLimit = points.map((p) => p.value > data.limit_c);

  const limitPlugin: Plugin<"line"> = {
    id: "controlLimit",
    afterDraw(chart) {
      const yScale = chart.scales.y;
      const { ctx, chartArea } = chart;
      const y = yScale.getPixelForValue(data.limit_c);
      ctx.save();
      ctx.strokeStyle = amber;
      ctx.setLineDash([5, 3]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(chartArea.left, y);
      ctx.lineTo(chartArea.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = amberInk;
      ctx.font = `600 11px ${monoFont.family}`;
      ctx.textAlign = "right";
      ctx.fillText(`${data.limit_c.toFixed(0)} °C limit`, chartArea.right - 4, y - 4);
      ctx.restore();
    },
  };

  const chartData: ChartData<"line"> = {
    labels: points.map((p) => p.lot_id),
    datasets: [
      {
        label: "Reflow peak temperature (°C)",
        data: points.map((p) => p.value),
        borderColor: green,
        tension: 0.1,
        pointRadius: 2,
        borderWidth: 1.5,
        pointBackgroundColor: overLimit.map((o) => (o ? red : green)),
        segment: {
          borderColor: (ctx: ScriptableLineSegmentContext) => (overLimit[ctx.p1DataIndex] ? red : green),
        },
      },
    ],
  };

  const options: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: monoFont,
        bodyFont: monoFont,
        callbacks: {
          label: (ctx) => `${ctx.label}: ${(ctx.parsed.y ?? 0).toFixed(1)} °C${
            overLimit[ctx.dataIndex] ? " (over limit)" : ""
          }`,
        },
      },
    },
    scales: {
      x: { ticks: { color: ink, font: monoFont, maxTicksLimit: 10 }, grid: { color: gridLine } },
      y: {
        title: { display: true, text: "°C", color: ink },
        ticks: { color: ink, font: monoFont },
        grid: { color: gridLine },
      },
    },
  };

  const nOver = overLimit.filter(Boolean).length;
  const caption =
    `Control chart of reflow peak temperature in degrees Celsius across ${points.length} lots, ` +
    `with a ${data.limit_c.toFixed(0)} °C control limit shown as a dashed line. ${nOver} lot(s) exceed the limit, shown in red.`;

  return (
    <figure className="m-0">
      <div role="img" aria-label={caption} className="h-64">
        <Line data={chartData} options={options} plugins={[limitPlugin]} aria-hidden="true" />
      </div>
      <figcaption className="mt-2 text-xs opacity-60">{caption}</figcaption>
    </figure>
  );
}
