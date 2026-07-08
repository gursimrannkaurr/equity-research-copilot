import type {
  TickerResponse,
  PeersResponse,
  ResearchNoteResponse,
  ChatResponse,
  ChatMessage,
  Metrics,
  Fundamentals,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore, use statusText
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export async function fetchTicker(symbol: string): Promise<TickerResponse> {
  const res = await fetch(
    `${API_BASE}/api/ticker/${encodeURIComponent(symbol)}`
  );
  return handle<TickerResponse>(res);
}

export async function fetchPeers(
  symbol: string,
  peers: string[]
): Promise<PeersResponse> {
  const query = peers.length ? `?peers=${encodeURIComponent(peers.join(","))}` : "";
  const res = await fetch(
    `${API_BASE}/api/ticker/${encodeURIComponent(symbol)}/peers${query}`
  );
  return handle<PeersResponse>(res);
}

export async function generateResearchNote(
  symbol: string,
  metrics?: Metrics,
  fundamentals?: Fundamentals
): Promise<ResearchNoteResponse> {
  const res = await fetch(`${API_BASE}/api/research-note`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, metrics, fundamentals }),
  });
  return handle<ResearchNoteResponse>(res);
}

export async function sendChatMessage(
  symbol: string,
  metrics: Metrics | undefined,
  history: ChatMessage[],
  message: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, metrics, history, message }),
  });
  return handle<ChatResponse>(res);
}
