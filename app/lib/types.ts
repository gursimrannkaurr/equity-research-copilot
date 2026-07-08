export interface PricePoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface Metrics {
  last_close: number | null;
  sma_50: number | null;
  sma_200: number | null;
  golden_cross: boolean | null;
  volatility_annualized: number | null;
  max_drawdown: number | null;
  rsi_14: number | null;
  return_1m: number | null;
  return_6m: number | null;
  return_1y: number | null;
}

export interface Fundamentals {
  trailing_pe: number | null;
  forward_pe: number | null;
  price_to_book: number | null;
  trailing_eps: number | null;
  market_cap: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  short_name: string | null;
  sector: string | null;
  industry: string | null;
  currency: string | null;
}

export interface TickerResponse {
  symbol: string;
  prices: PricePoint[];
  metrics: Metrics;
  fundamentals: Fundamentals;
}

export interface PeerRow {
  symbol: string;
  trailing_pe: number | null;
  forward_pe: number | null;
  price_to_book: number | null;
  roe: number | null;
  profit_margin: number | null;
  market_cap: number | null;
  debt_to_equity: number | null;
}

export interface HealthScoreComponent {
  score: number;
  reason: string;
  [key: string]: unknown;
}

export interface HealthScore {
  final_score: number;
  valuation: HealthScoreComponent;
  momentum: HealthScoreComponent;
  profitability: HealthScoreComponent;
  weights: { valuation: number; momentum: number; profitability: number };
}

export interface PeersResponse {
  symbol: string;
  peers: string[];
  ratio_table: PeerRow[];
  health_score: HealthScore;
}

export interface ResearchNoteResponse {
  text: string;
  disclaimer: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
}
