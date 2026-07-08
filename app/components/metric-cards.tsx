import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Metrics, Fundamentals } from "@/lib/types";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined) return "N/A";
  return `${(v * 100).toFixed(digits)}%`;
}

function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "N/A";
  return v.toFixed(digits);
}

function fmtLarge(v: number | null | undefined): string {
  if (v === null || v === undefined) return "N/A";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${v.toFixed(0)}`;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-zinc-500">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-lg font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

export function MetricCards({
  metrics,
  fundamentals,
}: {
  metrics: Metrics;
  fundamentals: Fundamentals;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      <MetricCard label="1M Return" value={fmtPct(metrics.return_1m)} />
      <MetricCard label="6M Return" value={fmtPct(metrics.return_6m)} />
      <MetricCard label="1Y Return" value={fmtPct(metrics.return_1y)} />
      <MetricCard
        label="Volatility (ann.)"
        value={fmtPct(metrics.volatility_annualized)}
      />
      <MetricCard label="RSI (14)" value={fmtNum(metrics.rsi_14, 1)} />
      <MetricCard label="Max Drawdown" value={fmtPct(metrics.max_drawdown)} />
      <MetricCard label="Trailing P/E" value={fmtNum(fundamentals.trailing_pe)} />
      <MetricCard label="Forward P/E" value={fmtNum(fundamentals.forward_pe)} />
      <MetricCard label="Market Cap" value={fmtLarge(fundamentals.market_cap)} />
      <MetricCard label="Profit Margin" value={fmtPct(fundamentals.profit_margin)} />
      <MetricCard label="ROE" value={fmtPct(fundamentals.roe)} />
      <MetricCard
        label="Trend"
        value={
          metrics.golden_cross === null
            ? "N/A"
            : metrics.golden_cross
            ? "Golden Cross"
            : "Death Cross"
        }
      />
    </div>
  );
}
