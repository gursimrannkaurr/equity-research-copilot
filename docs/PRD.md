# Product Requirements Document — Equity Research Copilot

## Problem statement

Individual learners, students, and career-switchers exploring equity
research (e.g. a Data Analyst building a portfolio piece) don't have a
free, transparent tool that combines: (a) real market data, (b) clearly
documented quantitative analytics, and (c) an AI layer that is honest about
what it does and doesn't know. Most "AI stock analysis" demos either use
paid data feeds, hide their formulas, or let an LLM hallucinate numbers.
This project demonstrates how to build a **zero-cost, fully transparent**
version of that workflow.

## Target user

- Primary: the project owner (Gursimran Kaur) — a Data Analyst using this
  as a portfolio piece to demonstrate data engineering, analytics design,
  API/full-stack development, and LLM-grounding skills to prospective
  employers.
- Secondary: anyone learning equity analysis basics who wants to see how
  common metrics (P/E, RSI, SMA, drawdown) are computed from raw data,
  with the formulas exposed rather than hidden behind a black box.

## Goals / features

1. Look up any publicly traded ticker (US exchanges, plus NSE India via the
   `.NS` suffix) and see 1-year price history with SMA overlays.
2. Compute and display standard technical metrics: trailing returns (1M/6M/1Y),
   annualized volatility, RSI(14), max drawdown, golden/death cross.
3. Display key fundamentals (P/E, P/B, EPS, market cap, margins, ROE,
   debt/equity, growth rates) pulled from free public data, with graceful
   "N/A" handling for missing fields.
4. Compare a ticker against a peer set (hardcoded sector map or user-supplied
   tickers) in a ratio table with visual heat-shading.
5. Compute a transparent, documented **composite health score (0-100)**
   from valuation, momentum, and profitability sub-scores.
6. Optionally generate an AI research note and support follow-up chat,
   using Gemini 2.5 Flash, strictly grounded in the computed metrics — with
   a rule-based fallback that works identically well with zero AI cost.
7. Run entirely on free-tier infrastructure: no paid data APIs, no paid
   LLM APIs, deployable on Vercel's free tier.

## Non-goals

- **Not investment advice.** No output from this app should be interpreted
  as a buy/sell/hold recommendation.
- **Not real-time / high-frequency data.** `yfinance` data can be delayed
  by minutes to (in edge cases) longer; this tool is not suitable for
  intraday trading decisions.
- **No brokerage integration.** No order placement, portfolio tracking
  tied to real accounts, or authentication against a brokerage.
- **No future price prediction / forecasting models.** The health score is
  a transparent, rule-based *descriptive* composite of current conditions,
  not a predictive model, and is explicitly documented as such.
- **No paid data or paid LLM usage.** Every dependency must have a free
  tier sufficient to run this project end-to-end at zero cost.

## Success metrics (portfolio-project framing)

- All analytics functions are unit-tested with hand-verifiable synthetic
  fixtures and pass with 100% green (`pytest`), independent of network
  access.
- `GET /api/ticker/{symbol}` returns clean, typed JSON (or a clean 4xx
  error) for both valid and invalid tickers — never a 500 stack trace.
- The frontend (`npm run build`) compiles with zero TypeScript/build errors
  regardless of backend/network availability at build time.
- The Gemini integration works correctly (falls back gracefully, never
  crashes) with **no API key configured**, since this project intentionally
  ships without a paid/keyed AI backend by default.
- Documentation (this PRD, ARCHITECTURE, DATA, DEPLOYMENT, DECISIONS,
  GLOSSARY, JOURNAL) is specific enough that another engineer could
  reproduce the build decisions and formulas without reading the source
  first.
