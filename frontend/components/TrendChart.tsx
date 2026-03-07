"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { MarketSnapshot } from "@/lib/api";

export function TrendChart({ data, compact = false }: { data: MarketSnapshot[]; compact?: boolean }) {
  const chartData = data.map((d) => ({
    name: d.symbol.replace("^", ""),
    probUp: Number((d.prob_up * 100).toFixed(2)),
    momentum: Number(d.momentum_7d.toFixed(2)),
  }));

  return (
    <div className="card trend-card">
      <h3>Stock Trend Signal</h3>
      <div style={{ width: "100%", height: compact ? 170 : 280 }}>
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Line type="monotone" dataKey="probUp" stroke="#22c55e" strokeWidth={3} />
            <Line type="monotone" dataKey="momentum" stroke="#38bdf8" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
