"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";
import type { PricePoint } from "@/lib/types";

interface Props {
  prices: PricePoint[];
  sma50: number | null;
  sma200: number | null;
}

export function PriceChart({ prices, sma50, sma200 }: Props) {
  // Build SMA overlay series as flat reference lines using the latest
  // computed SMA value (the API returns a single trailing SMA value, not a
  // full rolling series), rendered as constant lines across the chart.
  const data = prices.map((p) => ({
    date: p.date,
    close: p.close,
    sma50: sma50,
    sma200: sma200,
  }));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11 }}
            width={60}
          />
          <RechartsTooltip
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(2) : String(value ?? "")
            }
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2563eb"
            dot={false}
            name="Close"
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="sma50"
            stroke="#f59e0b"
            dot={false}
            name="SMA 50"
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
          <Line
            type="monotone"
            dataKey="sma200"
            stroke="#dc2626"
            dot={false}
            name="SMA 200"
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
