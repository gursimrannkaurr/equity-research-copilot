"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PeerRow } from "@/lib/types";

interface Props {
  symbol: string;
  defaultPeers: string[];
  onFetch: (peers: string[]) => void;
  ratioTable: PeerRow[];
  loading: boolean;
}

type NumericKey =
  | "trailing_pe"
  | "forward_pe"
  | "price_to_book"
  | "roe"
  | "profit_margin"
  | "market_cap"
  | "debt_to_equity";

const LOWER_IS_BETTER: NumericKey[] = ["trailing_pe", "forward_pe", "price_to_book", "debt_to_equity"];

function heatColor(rank: number, total: number): string {
  // rank 0 = best. Interpolate green (best) -> red (worst).
  if (total <= 1) return "";
  const t = rank / (total - 1);
  return `rgba(${Math.round(120 + t * 120)}, ${Math.round(200 - t * 150)}, 100, 0.25)`;
}

function computeRanks(rows: PeerRow[], key: NumericKey): Record<string, number> {
  const values = rows
    .map((r) => ({ symbol: r.symbol, value: r[key] }))
    .filter((v) => v.value !== null && v.value !== undefined) as { symbol: string; value: number }[];

  const lowerBetter = LOWER_IS_BETTER.includes(key);
  const sorted = [...values].sort((a, b) => (lowerBetter ? a.value - b.value : b.value - a.value));

  const ranks: Record<string, number> = {};
  sorted.forEach((v, idx) => {
    ranks[v.symbol] = idx;
  });
  return ranks;
}

function fmtCell(key: NumericKey, value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  if (key === "roe" || key === "profit_margin") return `${(value * 100).toFixed(1)}%`;
  if (key === "market_cap") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    return `$${(value / 1e6).toFixed(2)}M`;
  }
  return value.toFixed(2);
}

const COLUMNS: { key: NumericKey; label: string }[] = [
  { key: "trailing_pe", label: "P/E" },
  { key: "forward_pe", label: "Fwd P/E" },
  { key: "price_to_book", label: "P/B" },
  { key: "roe", label: "ROE" },
  { key: "profit_margin", label: "Margin" },
  { key: "market_cap", label: "Mkt Cap" },
  { key: "debt_to_equity", label: "D/E" },
];

export function PeerTable({ symbol, defaultPeers, onFetch, ratioTable, loading }: Props) {
  const [peerInput, setPeerInput] = useState(defaultPeers.join(", "));

  const rankMaps = COLUMNS.reduce<Record<string, Record<string, number>>>((acc, col) => {
    acc[col.key] = computeRanks(ratioTable, col.key);
    return acc;
  }, {});

  return (
    <div className="space-y-3">
      <div className="flex gap-2 items-center flex-wrap">
        <Input
          value={peerInput}
          onChange={(e) => setPeerInput(e.target.value)}
          placeholder="Comma-separated peer tickers, e.g. MSFT, GOOGL"
          className="max-w-md"
        />
        <Button
          disabled={loading}
          onClick={() =>
            onFetch(
              peerInput
                .split(",")
                .map((p) => p.trim())
                .filter(Boolean)
            )
          }
        >
          {loading ? "Loading..." : "Compare Peers"}
        </Button>
      </div>

      {ratioTable.length > 0 && (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                {COLUMNS.map((c) => (
                  <TableHead key={c.key}>{c.label}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {ratioTable.map((row) => (
                <TableRow key={row.symbol} className={row.symbol === symbol ? "font-semibold" : ""}>
                  <TableCell>{row.symbol}</TableCell>
                  {COLUMNS.map((c) => {
                    const rank = rankMaps[c.key][row.symbol];
                    const total = Object.keys(rankMaps[c.key]).length;
                    const style =
                      rank !== undefined
                        ? { backgroundColor: heatColor(rank, total) }
                        : undefined;
                    return (
                      <TableCell key={c.key} style={style}>
                        {fmtCell(c.key, row[c.key])}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
