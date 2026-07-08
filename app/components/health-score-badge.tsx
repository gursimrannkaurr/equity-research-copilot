"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { HealthScore } from "@/lib/types";

function scoreColor(score: number): string {
  if (score >= 70) return "bg-green-600 hover:bg-green-600";
  if (score >= 40) return "bg-amber-500 hover:bg-amber-500";
  return "bg-red-600 hover:bg-red-600";
}

export function HealthScoreBadge({ healthScore }: { healthScore: HealthScore }) {
  const [expanded, setExpanded] = useState(false);
  const { final_score, valuation, momentum, profitability, weights } = healthScore;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger
            render={
              <Badge
                className={`${scoreColor(final_score)} text-white text-sm px-3 py-1 cursor-pointer`}
                onClick={() => setExpanded((v) => !v)}
              />
            }
          >
            Health Score: {final_score.toFixed(1)} / 100
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            Weighted composite: {(weights.valuation * 100).toFixed(0)}% valuation +{" "}
            {(weights.momentum * 100).toFixed(0)}% momentum +{" "}
            {(weights.profitability * 100).toFixed(0)}% profitability. Click badge for
            details.
          </TooltipContent>
        </Tooltip>
        <button
          className="text-xs text-zinc-500 underline"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "hide formula" : "show formula"}
        </button>
      </div>

      {expanded && (
        <div className="rounded-md border p-3 text-xs space-y-2 bg-zinc-50 dark:bg-zinc-900">
          <p className="font-medium">
            Final = clamp(0.30 × Valuation + 0.35 × Momentum + 0.35 × Profitability, 0, 100)
          </p>
          <div>
            <p className="font-semibold">
              Valuation (30%): {valuation.score.toFixed(1)}
            </p>
            <p className="text-zinc-500">{valuation.reason}</p>
            <p className="text-zinc-400">
              score = clamp(100 − ratio × 50, 0, 100), ratio = target P/E ÷ peer avg P/E.
              Missing/negative P/E ⇒ neutral 50.
            </p>
          </div>
          <div>
            <p className="font-semibold">
              Momentum (35%): {momentum.score.toFixed(1)}
            </p>
            <p className="text-zinc-500">{momentum.reason}</p>
            <p className="text-zinc-400">
              Average of trend component (price vs SMA50/SMA200: 100 / 60 / 20) and RSI
              band component (RSI 40–60 ⇒ 100, 30–40 or 60–70 ⇒ 70, else ⇒ 40).
            </p>
          </div>
          <div>
            <p className="font-semibold">
              Profitability (35%): {profitability.score.toFixed(1)}
            </p>
            <p className="text-zinc-500">{profitability.reason}</p>
            <p className="text-zinc-400">
              Average of profit-margin bucket and ROE bucket, each: ≥20% ⇒ 100, 10–20%
              ⇒ 75, 0–10% ⇒ 50, &lt;0% ⇒ 20.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
