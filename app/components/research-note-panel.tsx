"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { generateResearchNote, ApiError } from "@/lib/api";
import type { Metrics, Fundamentals } from "@/lib/types";

interface Props {
  symbol: string;
  metrics: Metrics;
  fundamentals: Fundamentals;
}

export function ResearchNotePanel({ symbol, metrics, fundamentals }: Props) {
  const [text, setText] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await generateResearchNote(symbol, metrics, fundamentals);
      setText(res.text);
      setDisclaimer(res.disclaimer);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate research note.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Research Note</CardTitle>
        <Button onClick={handleGenerate} disabled={loading}>
          {loading ? "Generating..." : "Generate Research Note"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {text && (
          <div className="text-sm whitespace-pre-wrap leading-relaxed">{text}</div>
        )}
        {!text && !error && (
          <p className="text-sm text-zinc-500">
            No research note generated yet. Click the button above — this works
            with or without a configured GEMINI_API_KEY (falls back to a
            rule-based summary).
          </p>
        )}
        <p className="text-xs text-zinc-400 pt-2 border-t mt-2">
          {disclaimer ?? "Educational project. Not investment advice."}
        </p>
      </CardContent>
    </Card>
  );
}
