"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sendChatMessage, ApiError } from "@/lib/api";
import type { ChatMessage, Metrics } from "@/lib/types";

interface Props {
  symbol: string;
  metrics: Metrics;
}

export function ChatDrawer({ symbol, metrics }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    const nextHistory: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextHistory);
    setInput("");
    setLoading(true);
    try {
      const res = await sendChatMessage(symbol, metrics, messages, trimmed);
      setMessages([...nextHistory, { role: "assistant", content: res.reply }]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Chat request failed.";
      setMessages([...nextHistory, { role: "assistant", content: `Error: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={<Button variant="outline" />}>
        Ask about {symbol}
      </SheetTrigger>
      <SheetContent className="flex flex-col w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Chat — {symbol}</SheetTitle>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-zinc-500">
              Ask a follow-up question grounded in the currently computed
              metrics for {symbol}. Works with or without a configured
              GEMINI_API_KEY.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-md p-2 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-blue-50 dark:bg-blue-950 ml-6"
                  : "bg-zinc-100 dark:bg-zinc-800 mr-6"
              }`}
            >
              {m.content}
            </div>
          ))}
        </div>
        <SheetFooter className="flex-row gap-2 items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />
          <Button onClick={handleSend} disabled={loading}>
            {loading ? "..." : "Send"}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
