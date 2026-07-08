# Data sources

## yfinance (primary and only market-data source)

This project uses [`yfinance`](https://github.com/ranaroussi/yfinance), an
**unofficial, community-maintained Python wrapper** around Yahoo Finance's
public (undocumented) web endpoints. It is free and requires no API key,
which is why it was chosen for a zero-cost portfolio project.

**Important caveats** (also repeated in the README/UI disclaimers):

- Yahoo Finance can change its endpoints or rate-limit/block requests
  (especially from shared/datacenter IPs — see `docs/DEPLOYMENT.md` for the
  serverless implications) at any time, without notice, since this is not
  an official, contracted data feed.
- Data can be delayed and is **not suitable for real-time or
  high-frequency trading decisions**.
- Fundamentals (`.info`) fields are inconsistently populated across
  tickers and exchanges — a field like `debtToEquity` may exist for one
  company and be `None` for another with no error raised. All extraction
  code in `api/analytics.py` uses `.get(key)` with a `None` default and is
  designed to degrade gracefully (render "N/A" in the UI) rather than
  crash.
- This project is **not for production trading use**. It's a learning /
  portfolio artifact.

## Fields pulled and their meaning

### From `Ticker.history(period="1y")` (OHLCV)

| Field | Meaning |
|---|---|
| Open/High/Low/Close | Daily price range and closing price |
| Volume | Shares traded that day |

Derived from this: 1M/6M/1Y returns, annualized volatility, SMA(50),
SMA(200), golden/death cross, max drawdown, RSI(14). See
`docs/ARCHITECTURE.md` for exact formulas.

### From `Ticker.info` (fundamentals dict)

| App field | yfinance key | Meaning |
|---|---|---|
| `trailing_pe` | `trailingPE` | Price ÷ trailing 12-month EPS |
| `forward_pe` | `forwardPE` | Price ÷ analyst-estimated forward EPS |
| `price_to_book` | `priceToBook` | Price ÷ book value per share |
| `trailing_eps` | `trailingEps` | Trailing 12-month earnings per share |
| `market_cap` | `marketCap` | Shares outstanding × price |
| `profit_margin` | `profitMargins` | Net income ÷ revenue (fraction) |
| `roe` | `returnOnEquity` | Net income ÷ shareholder equity (fraction) |
| `debt_to_equity` | `debtToEquity` | Total debt ÷ shareholder equity |
| `revenue_growth` | `revenueGrowth` | YoY revenue growth (fraction) |
| `earnings_growth` | `earningsGrowth` | YoY earnings growth (fraction) |
| `short_name` | `shortName` | Company display name |
| `sector` / `industry` | `sector` / `industry` | GICS-like classification used for peer resolution |

## Hardcoded sector → peer ticker map

Defined in `api/analytics.py::SECTOR_PEER_MAP`:

```python
{
    "tech": ["AAPL", "MSFT", "GOOGL"],
    "banking": ["JPM", "BAC"],
    "auto": ["TSLA", "F"],
    "fmcg": ["PG", "KO"],
}
```

`resolve_peers(sector, explicit_peers)` matches the ticker's `sector`
string (from `.info`) case-insensitively/substring against these keys.
Explicit peer tickers passed by the user always override this map.

### Limitations of the hardcoded map

- Only 4 sectors are covered; any ticker outside tech/banking/auto/FMCG
  gets no automatic peers unless the user supplies explicit tickers.
- Yahoo's `sector` string doesn't always contain the literal substring
  ("tech", "banking", etc.) used for matching — e.g. Yahoo may report
  "Technology" (which matches "tech") but a sector like "Financial
  Services" would NOT match "banking" and would return no peers.
- The map is static and not derived from any live sector/industry
  taxonomy API (that would cost money or require a paid data source) — a
  production version would likely use a proper GICS/ICB sector database.
- Peer sets are small (2-3 tickers) and chosen for illustrative diversity,
  not comprehensive competitive coverage.
