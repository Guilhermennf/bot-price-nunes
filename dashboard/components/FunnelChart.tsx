"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Horizontal bars, single ordinal hue (funnel of one run) + direct labels.
export default function FunnelChart({
  data,
}: {
  data: { stage: string; count: number }[];
}) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 36, left: 8, bottom: 0 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="stage"
            width={110}
            tick={{ fill: "var(--ink-2)", fontSize: 12 }}
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
            formatter={(value) => [String(value), "deals"]}
          />
          <Bar
            dataKey="count"
            fill="var(--series-1)"
            radius={[0, 4, 4, 0]}
            maxBarSize={18}
            label={{
              position: "right",
              fill: "var(--ink)",
              fontSize: 12,
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
