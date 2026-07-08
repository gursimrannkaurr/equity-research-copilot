# Architecture

## Data flow

```
yfinance (Yahoo Finance, unofficial/free)
   │  Ticker(symbol).history(period="1y")  +  Ticker(symbol).info
   ▼
api/market_data.py
   - in-process dict cache keyed by (symbol, "history:<period>") or (symbol, "info")
   - TTL = 300 seconds (see "Caching strategy" below)
   - wraps all yfinance exceptions into MarketDataError(message, status_code)
   ▼
api/analytics.py
   - compute_price_metrics(history)      -> returns, SMA50/200, golden cross,
                                             volatility, max drawdown, RSI(14)
   - extract_fundamentals(info)          -> P/E, P/B, EPS, market cap, margins,
                                             ROE, D/E, growth (all via .get(), never raises)
   - resolve_peers(sector, explicit)     -> hardcoded sector->peer map, explicit override
   - build_ratio_table(rows)             -> flat peer comparison rows
   - compute_health_score(...)           -> composite 0-100 score (see formula below)
   ▼
api/index.py (FastAPI)
   - GET  /api/ticker/{symbol}
   - GET  /api/ticker/{symbol}/peers?peers=A,B,C
   - POST /api/research-note
   - POST /api/chat
   - CORS enabled for http://localhost:3000
   - all MarketDataError instances become clean HTTPException(status_code, detail) JSON
   ▼
app/ (Next.js App Router, client-side fetches only)
   - price chart (Recharts) with SMA50/SMA200 overlay
   - metric cards, health-score badge w/ expandable formula panel
   - peer comparison table with inline heat-shading
   - research note panel (POST /api/research-note)
   - chat drawer (POST /api/chat, stateless history resent each call)

api/gemini_client.py (grounding path, called from api/index.py)
   - serializes metrics/fundamentals/peers into a JSON context block
   - injects a strict anti-hallucination system instruction (verbatim below)
   - falls back to templated rule-based text if GEMINI_API_KEY is unset OR
     any exception occurs during the Gemini call
```

## API contract (example JSON per endpoint)

### `GET /api/ticker/{symbol}`

Response `200`:

```json
{
  "symbol": "AAPL",
  "prices": [
    {"date": "2025-07-08", "open": 210.1, "high": 212.4, "low": 209.0, "close": 211.9, "volume": 51234000}
  ],
  "metrics": {
    "last_close": 313.39,
    "sma_50": 295.85,
    "sma_200": 271.44,
    "golden_cross": true,
    "volatility_annualized": 0.3763,
    "max_drawdown": -0.138,
    "rsi_14": 59.49,
    "return_1m": 0.0197,
    "return_6m": 0.1748,
    "return_1y": null
  },
  "fundamentals": {
    "trailing_pe": 37.94,
    "forward_pe": 32.61,
    "price_to_book": 43.17,
    "trailing_eps": 8.26,
    "market_cap": 4602870628352,
    "profit_margin": 0.2715,
    "roe": 1.4147,
    "debt_to_equity": 79.55,
    "revenue_growth": 0.166,
    "earnings_growth": 0.218,
    "short_name": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "currency": "USD"
  }
}
```

Error (invalid ticker), `404`:

```json
{"detail": "No price data found for ticker 'ZZZZZ'. It may be invalid or delisted."}
```

### `GET /api/ticker/{symbol}/peers?peers=MSFT,GOOGL`

```json
{
  "symbol": "AAPL",
  "peers": ["MSFT", "GOOGL"],
  "ratio_table": [
    {"symbol": "AAPL", "trailing_pe": 37.94, "forward_pe": 32.61, "price_to_book": 43.17, "roe": 1.41, "profit_margin": 0.27, "market_cap": 4602870628352, "debt_to_equity": 79.55},
    {"symbol": "MSFT", "trailing_pe": 22.82, "forward_pe": 19.80, "price_to_book": 6.87, "roe": 0.34, "profit_margin": 0.39, "market_cap": 2847616270336, "debt_to_equity": 30.27}
  ],
  "health_score": {
    "final_score": 77.4,
    "valuation": {"score": 79.9, "reason": "Target P/E 37.94 vs peer average 25.22 (ratio 1.50)."},
    "momentum": {"score": 100.0, "trend_component": 100.0, "rsi_component": 100.0, "reason": "..."},
    "profitability": {"score": 62.5, "margin_component": 75.0, "roe_component": 100.0, "reason": "..."},
    "weights": {"valuation": 0.3, "momentum": 0.35, "profitability": 0.35}
  }
}
```

If a peer ticker cannot be resolved, it is silently dropped from the ratio
table row set (its fundamentals become all-null) rather than failing the
whole request.

### `POST /api/research-note`

Request:

```json
{"symbol": "AAPL"}
```

(`metrics`, `fundamentals`, `peers` are optional — if omitted, the server
recomputes them via `_fetch_symbol_bundle`.)

Response `200`:

```json
{
  "text": "## Business Snapshot\n...\n\nEducational project. Not investment advice.",
  "disclaimer": "Educational project. Not investment advice."
}
```

### `POST /api/chat`

Request:

```json
{
  "symbol": "AAPL",
  "metrics": {"rsi_14": 55},
  "history": [{"role": "user", "content": "What's the trend?"}],
  "message": "Is it overbought?"
}
```

Response `200`:

```json
{"reply": "...\n\nEducational project. Not investment advice."}
```

## Health score — exact formula (mirrors `api/analytics.py`)

```
Final = clamp(
    0.30 * Valuation +
    0.35 * Momentum +
    0.35 * Profitability,
    0, 100
)
```

### Valuation (30%)

```
peer_valid = [p for p in peer_pes if p is not None and p > 0]
if target_pe is None or target_pe <= 0 or not peer_valid:
    score = 50   # neutral, reason recorded
else:
    peer_avg_pe = mean(peer_valid)
    ratio = target_pe / peer_avg_pe
    score = clamp(100 - ratio * 50, 0, 100)
```

Examples: ratio 1.0 (at peer average) → 50; ratio 0.5 (half peer average,
cheaper) → 75; ratio 2.0 (2x peer average, pricier) → 0.

### Momentum (35%)

Average of two 0-100 components:

**Trend component** (price vs SMA50/SMA200):
- price > SMA50 AND price > SMA200 → 100
- price > SMA50 XOR price > SMA200 → 60
- price < SMA50 AND price < SMA200 → 20
- any input missing → 50 (neutral)

**RSI banding component**:
- RSI in [40, 60] → 100 (healthy neutral)
- RSI in [30, 40) or (60, 70] → 70 (mild oversold/overbought)
- RSI < 30 or RSI > 70 → 40 (oversold/overbought risk)
- RSI missing → 50 (neutral)

`momentum_score = clamp((trend_component + rsi_component) / 2, 0, 100)`

### Profitability (35%)

Average of two 0-100 components, each using the same bucket thresholds on
a fraction value (e.g. 0.20 = 20%):

- value ≥ 0.20 → 100
- 0.10 ≤ value < 0.20 → 75
- 0.00 ≤ value < 0.10 → 50
- value < 0.00 → 20
- missing → 50 (neutral)

Applied independently to `profit_margin` and `roe`, then averaged.

## RSI method (documented choice)

We use the **simple rolling-average** method (not Wilder/exponential
smoothing) for RSI(14):

```
delta = Close.diff()
gains = delta.clip(lower=0)
losses = -delta.clip(upper=0)
avg_gain = gains.rolling(14).mean()
avg_loss = losses.rolling(14).mean()
RS = avg_gain / avg_loss
RSI = 100 - 100 / (1 + RS)
```

Special cases: `avg_loss == 0 and avg_gain > 0` → RSI = 100;
`avg_loss == 0 and avg_gain == 0` → RSI = 50 (flat/no movement).

This was chosen over Wilder smoothing specifically because it is easy to
hand-verify in unit tests (no recursive/exponential state to replicate) —
appropriate for a portfolio-education tool that is explicitly not meant
for high-frequency trading precision. See `memory/DECISIONS.md`.

## Gemini grounding strategy

**Model**: `gemini-2.5-flash` via `google-generativeai`, `GEMINI_API_KEY`
read from environment at call time (never hardcoded, never required).

**System instruction (verbatim, sent on every model init)**:

> You are an equity research assistant embedded in a portfolio project.
> Only use the numbers provided below. Never invent or estimate financial
> figures not given to you. If information is missing, say so explicitly.
> Always keep a neutral, educational tone. Never phrase output as
> personalized investment advice.

**Injected content**: every prompt embeds a JSON block
(`{"ticker": ..., "metrics": {...}, "fundamentals": {...}, "peers": [...]}`)
built directly from the same `analytics.py` output used to render the UI —
this is the entire numeric "ground truth" available to the model. The
per-call prompt repeats the anti-hallucination instruction ("Only use the
DATA block below; never invent numbers... If the answer requires data not
present, say so explicitly.") so grounding survives even if a client only
partially initializes the system instruction.

**Anti-hallucination fallback chain**:
1. No `GEMINI_API_KEY` in env → skip the Gemini SDK entirely, use the
   rule-based templated text (same structure/sections), prefixed "This is a
   rule-based summary — set GEMINI_API_KEY for AI-generated analysis."
2. `GEMINI_API_KEY` present but the call raises any exception (network,
   rate limit, auth, empty response) → same rule-based templated text,
   prefixed "AI analyst is temporarily unavailable, showing rule-based
   summary."
3. In both cases, the hardcoded disclaimer "Educational project. Not
   investment advice." is always appended, regardless of source.

No exception from `google.generativeai` is ever allowed to propagate out
of `gemini_client.py` — every public function (`generate_research_note`,
`chat`, `explain_peer_comparison`) wraps its Gemini call in `try/except`.

## Caching strategy / TTL

`api/market_data.py` keeps an in-process Python dict:
`{(symbol, "history:<period>"|"info"): (value, inserted_at_epoch)}`.
TTL is **300 seconds (5 minutes)** — long enough to avoid hammering Yahoo's
unofficial endpoints on repeated requests for the same ticker within a
session, short enough that prices don't go too stale for a research tool
(not a trading tool). This is a plain dict, not Redis/Memcached — see
`memory/DECISIONS.md` for the tradeoff rationale. On serverless (Vercel),
this cache resets on every cold start; documented as a known limitation in
`docs/DEPLOYMENT.md`, not a bug.

## Rate-limit / failure handling

- All yfinance calls are wrapped in `try/except Exception` inside
  `market_data.py` and converted to `MarketDataError(message, status_code)`.
  Empty/invalid results become 404; unexpected exceptions become 502.
- FastAPI route handlers catch `MarketDataError` and re-raise as
  `HTTPException(status_code, detail=message)` — this guarantees clean
  JSON error bodies, never a raw 500 traceback, for the two most common
  Yahoo Finance failure modes: invalid ticker and rate-limit/HTTP 429.
- The Gemini client applies the same defensive pattern for AI rate limits
  (see "Gemini grounding strategy" above).
