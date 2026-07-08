"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceChart } from "@/components/price-chart";
import { MetricCards } from "@/components/metric-cards";
import { HealthScoreBadge } from "@/components/health-score-badge";
import { PeerTable } from "@/components/peer-table";
import { ResearchNotePanel } from "@/components/research-note-panel";
import { ChatDrawer } from "@/components/chat-drawer";
import { fetchTicker, fetchPeers, ApiError } from "@/lib/api";
import type { TickerResponse, PeersResponse } from "@/lib/types";

export default function Home() {
  const [symbolInput, setSymbolInput] = useState("AAPL");
  const [ticker, setTicker] = useState<TickerResponse | null>(null);
  const [peersData, setPeersData] = useState<PeersResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [peersLoading, setPeersLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    const symbol = symbolInput.trim();
    if (!symbol) return;
    setLoading(true);
    setError(null);
    setPeersData(null);
    try {
      const data = await fetchTicker(symbol);
      setTicker(data);
    } catch (err) {
      setTicker(null);
      setError(
        err instanceof ApiError
          ? `${err.message} (status ${err.status})`
          : "Failed to fetch ticker data. Is the API server running?"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handlePeers(peers: string[]) {
    if (!ticker) return;
    setPeersLoading(true);
    try {
      const data = await fetchPeers(ticker.symbol, peers);
      setPeersData(data);
    } catch (err) {
      setPeersData(null);
      setError(
        err instanceof ApiError ? err.message : "Failed to fetch peer comparison."
      );
    } finally {
      setPeersLoading(false);
    }
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Equity Research Copilot</h1>
        <p className="text-sm text-zinc-500">
          Free market data (yfinance) + rule-based analytics + optional
          Gemini-grounded research notes. Educational project — not
          investment advice.
        </p>
      </div>

      <div className="flex gap-2 items-center flex-wrap">
        <Input
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          placeholder="Ticker symbol, e.g. AAPL, MSFT, or RELIANCE.NS"
          className="max-w-xs"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
        />
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? "Loading..." : "Search"}
        </Button>
        <p className="text-xs text-zinc-400">
          Use the .NS suffix for NSE India tickers (e.g. RELIANCE.NS).
        </p>
      </div>

      {error && (
        <Card className="border-red-300">
          <CardContent className="pt-4 text-sm text-red-600">{error}</CardContent>
        </Card>
      )}

      {ticker && (
        <div className="space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-xl font-semibold">
                {ticker.fundamentals.short_name ?? ticker.symbol} ({ticker.symbol})
              </h2>
              <p className="text-sm text-zinc-500">
                {ticker.fundamentals.sector ?? "N/A"} / {ticker.fundamentals.industry ?? "N/A"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {peersData && <HealthScoreBadge healthScore={peersData.health_score} />}
              <ChatDrawer symbol={ticker.symbol} metrics={ticker.metrics} />
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Price History (1Y) with SMA Overlay</CardTitle>
            </CardHeader>
            <CardContent>
              <PriceChart
                prices={ticker.prices}
                sma50={ticker.metrics.sma_50}
                sma200={ticker.metrics.sma_200}
              />
            </CardContent>
          </Card>

          <MetricCards metrics={ticker.metrics} fundamentals={ticker.fundamentals} />

          <Card>
            <CardHeader>
              <CardTitle>Peer Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <PeerTable
                symbol={ticker.symbol}
                defaultPeers={[]}
                onFetch={handlePeers}
                ratioTable={peersData?.ratio_table ?? []}
                loading={peersLoading}
              />
              {!peersData && (
                <p className="text-xs text-zinc-400 mt-2">
                  Leave blank to use the built-in sector/peer map, or enter
                  explicit tickers (comma-separated).
                </p>
              )}
            </CardContent>
          </Card>

          <ResearchNotePanel
            symbol={ticker.symbol}
            metrics={ticker.metrics}
            fundamentals={ticker.fundamentals}
          />
        </div>
      )}
    </main>
  );
}
