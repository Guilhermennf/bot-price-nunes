"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Single series: series-1 blue, no legend (the card title names it).
export default function PostsChart({
  data,
}: {
  data: { day: string; count: number }[];
}) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis
            dataKey="day"
            tick={{ fill: "var(--viz-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
            interval={1}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "var(--viz-muted)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "var(--grid)", opacity: 0.4 }}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--viz-border)",
              borderRadius: 8,
              color: "var(--ink)",
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--ink-2)" }}
            formatter={(value) => [String(value), "ofertas"]}
          />
          <Bar
            dataKey="count"
            fill="var(--series-1)"
            radius={[4, 4, 0, 0]}
            maxBarSize={22}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
