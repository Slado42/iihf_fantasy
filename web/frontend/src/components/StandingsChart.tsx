import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { StandingEntry } from "../types";

const COLORS = [
  "#f59e0b", "#60a5fa", "#34d399", "#f87171",
  "#a78bfa", "#fb923c", "#e879f9", "#2dd4bf",
];

interface Props {
  standings: StandingEntry[];
  currentUserId?: string;
}

export default function StandingsChart({ standings, currentUserId }: Props) {
  if (standings.length === 0) return null;

  const allDays = [
    ...new Set(standings.flatMap((s) => Object.keys(s.scores_by_day).map(Number))),
  ].sort((a, b) => a - b);

  const chartData = allDays.map((day) => {
    const point: Record<string, number> = { day };
    for (const entry of standings) {
      let cum = 0;
      for (const d of allDays) {
        if (d > day) break;
        cum += entry.scores_by_day[d] ?? 0;
      }
      point[entry.username] = parseFloat(cum.toFixed(1));
    }
    return point;
  });

  return (
    <div className="bg-navy-800 rounded-xl p-4 mt-6">
      <h2 className="text-sm font-semibold text-gray-400 mb-3">Cumulative Points</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="day"
            tick={{ fill: "#9ca3af", fontSize: 12 }}
            label={{ value: "Day", position: "insideBottomRight", offset: -4, fill: "#9ca3af", fontSize: 12 }}
          />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} width={40} />
          <Tooltip
            contentStyle={{ background: "#0f2744", border: "1px solid #1e3a5f", borderRadius: 8 }}
            labelStyle={{ color: "#9ca3af" }}
            itemStyle={{ color: "#e5e7eb" }}
            formatter={(v) => typeof v === "number" ? v.toFixed(1) : v}
            labelFormatter={(day) => `Day ${day}`}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
          {standings.map((entry, i) => (
            <Line
              key={entry.user_id}
              type="monotone"
              dataKey={entry.username}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={entry.user_id === currentUserId ? 2.5 : 1.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
