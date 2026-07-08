# Architecture Decision Records

Lightweight ADR-style log of key build decisions for the Equity Research
Copilot project.

---

## ADR-001: `yfinance` over paid market-data APIs

**Decision**: Use `yfinance` (unofficial, free, no API key) as the sole
market-data source instead of a paid provider (Alpha Vantage premium,
Polygon.io, IEX Cloud, etc.).

**Rationale**: Hard zero-cost constraint for a portfolio project.
`yfinance` covers OHLCV history and a reasonably rich fundamentals `.info`
dict for free, with no signup friction. Tradeoff: unofficial/unsupported,
can be rate-limited or break if Yahoo changes its endpoints — documented
extensively in `docs/DATA.md` and `docs/DEPLOYMENT.md`.

## ADR-002: Rule-based health score over an ML model

**Decision**: The composite 0-100 health score is a fully transparent,
weighted rule-based formula (30% valuation / 35% momentum / 35%
profitability), not a trained ML model.

**Rationale**: (1) No labeled training data or ground truth for "correct"
stock health exists without introducing bias/overfitting risk; (2) a
transparent formula is auditable and explainable in the UI (the
expandable "show formula" panel), which better serves the educational/demo
purpose than an opaque model; (3) keeps the project dependency-light (no
model training pipeline, no model file to version/serve).

## ADR-003: Stateless chat history, no database

**Decision**: `/api/chat` is stateless — the frontend resends the full
conversation history on every call; there is no server-side session store
or database.

**Rationale**: Zero infrastructure cost (no Postgres/Redis/etc. to
provision), and it matches the small-scale, single-session usage pattern
of a portfolio demo. Tradeoff: conversation history is lost on page reload
and can grow the request payload for very long conversations (mitigated by
truncating to the last 10 turns in `gemini_client.chat`).

## ADR-004: `gemini-2.5-flash` model choice

**Decision**: Use Google's `gemini-2.5-flash` model specifically (not Pro
or another provider) via `google-generativeai`.

**Rationale**: Flash models are optimized for low latency/cost and are
available on Google's free tier, which fits the zero-cost constraint.
Pro-tier models and other providers (OpenAI, Anthropic) either require
paid API keys or have much stricter free-tier limits at the time of
building. The model name is centralized as `MODEL_NAME` in
`gemini_client.py` for easy future swapping.

## ADR-005: In-process TTL cache over Redis/Memcached

**Decision**: `api/market_data.py` uses a plain Python dict keyed by
`(symbol, endpoint)` with a 300-second TTL, instead of an external cache
service.

**Rationale**: Zero additional infrastructure/cost, trivial to implement
and test, and sufficient for the request volume of a portfolio demo.
Documented tradeoff: resets on every serverless cold start and isn't
shared across concurrent instances (see `docs/DEPLOYMENT.md`). A
production system handling real traffic would use Vercel KV or Upstash
Redis instead.

## ADR-006: Hardcoded sector/peer map over a dynamic peer-discovery API

**Decision**: `SECTOR_PEER_MAP` in `analytics.py` is a static Python dict
covering 4 sectors (tech, banking, auto, FMCG) with 2-3 peer tickers each,
rather than calling a live sector/industry classification API.

**Rationale**: No free API reliably provides comprehensive, accurate
GICS/ICB-style peer sets. A small hardcoded map is transparent, fast, and
sufficient to demonstrate the peer-comparison feature end-to-end. Users
can always override with explicit peer tickers via the UI. Limitations are
documented in `docs/DATA.md`.

## ADR-007: Prompt-grounding anti-hallucination design

**Decision**: Every Gemini prompt (research note, chat, peer explanation)
embeds a structured JSON block of exactly the metrics/fundamentals/peers
computed by `analytics.py`, with an explicit system instruction and a
per-call reminder: "Only use the numbers provided below. Never invent or
estimate financial figures not given to you. If information is missing,
say so explicitly."

**Rationale**: The single biggest risk of an LLM-powered finance tool is
hallucinated numbers presented as fact. Grounding the prompt in exactly
the same JSON payload rendered in the UI means the model has no incentive
or opportunity to invent figures that aren't already visible to the user
— and if it does anyway, the discrepancy is easy to spot by comparing
against the metric cards on the same page.

## ADR-008: Next.js + FastAPI hybrid on Vercel

**Decision**: Deploy as one Vercel project combining a Next.js frontend
(`@vercel/next`) and a FastAPI Python serverless function
(`@vercel/python`), wired via a single root-level `vercel.json`, instead of
two separate deployments (e.g. a separate Render/Railway backend).

**Rationale**: Keeps the entire project on a single free-tier platform
(Vercel) with one deploy step, avoiding CORS/hosting complexity of
managing two providers. Tradeoff: Python cold starts and yfinance
datacenter-IP throttling are more likely on Vercel's serverless functions
than a long-running backend server — documented in `docs/DEPLOYMENT.md`.

## ADR-009: RSI computed via simple rolling average, not Wilder smoothing

**Decision**: `compute_rsi` in `analytics.py` uses a plain rolling-window
mean of gains/losses, not the classic Wilder exponential smoothing method
most trading platforms use by default.

**Rationale**: The simple method is deterministic and trivially
hand-verifiable in unit tests (`tests/test_analytics.py::test_rsi_hand_computed_example`)
without needing to replicate recursive/exponential smoothing state. Given
this tool is explicitly documented as not for high-frequency/precision
trading use, the small numeric difference from Wilder's method is an
acceptable tradeoff for testability and code simplicity. Documented
verbatim in the `compute_rsi` docstring and in `docs/ARCHITECTURE.md`.

## ADR-010: Cache TTL value of 300 seconds (5 minutes)

**Decision**: `CACHE_TTL_SECONDS = 300` in `market_data.py`.

**Rationale**: Balances two goals: (1) avoid re-hitting Yahoo Finance's
unofficial endpoints on every single page interaction within a short
browsing session (reduces rate-limit risk), and (2) keep data fresh enough
for a research tool where users expect roughly current, not stale, prices.
5 minutes was chosen as a reasonable middle ground without any formal
SLA requirement, since this is explicitly not a real-time trading tool.

## ADR-011: Peer table heat-shading implemented with inline styles, no chart library

**Decision**: The peer comparison table's green/red heat-shading is
computed client-side in `components/peer-table.tsx` using plain rank-based
color interpolation and inline `style` attributes, rather than pulling in
an additional charting/heatmap library.

**Rationale**: Recharts (already a dependency) doesn't provide table
heatmap primitives, and adding a second visualization library purely for
per-cell shading would be disproportionate to the feature. A small,
explicit rank→color function keeps the bundle lean and the logic
auditable.
