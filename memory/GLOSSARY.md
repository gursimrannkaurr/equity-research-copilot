# Glossary

Plain-language definitions of the finance and technical terms used
throughout this project, written for a non-technical reader.

**P/E ratio (Price-to-Earnings)** — How much investors are paying for
$1 of a company's annual profit. A P/E of 30 means the stock price is 30
times the company's earnings per share. Lower isn't automatically
"better" — it depends on growth expectations and the industry — but it's
a common way to compare how "expensive" different companies are relative
to their profits.

**Forward P/E** — Same idea as P/E, but using *analysts' estimated future*
earnings instead of the last 12 months of actual earnings.

**P/B ratio (Price-to-Book)** — Stock price divided by the company's book
value (assets minus liabilities) per share. Used to gauge how much the
market is paying above (or below) a company's accounting net worth.

**EPS (Earnings Per Share)** — A company's total profit divided by its
number of shares outstanding. One of the most basic profitability
measures.

**Market Cap (Market Capitalization)** — The total value of all a
company's shares (share price × number of shares). A rough measure of
company size.

**ROE (Return on Equity)** — How efficiently a company turns
shareholders' invested money into profit, expressed as a percentage
(net income ÷ shareholder equity).

**Profit Margin** — What percentage of revenue actually becomes profit,
after all costs (net income ÷ revenue).

**Debt-to-Equity** — How much a company relies on borrowed money (debt)
versus money from shareholders (equity) to finance itself. Higher
generally means more financial risk, but "normal" levels vary a lot by
industry.

**SMA (Simple Moving Average)** — The average closing price over the last
N trading days (e.g. the last 50 or 200 days). It smooths out day-to-day
noise to show the underlying trend.

**Golden Cross / Death Cross** — When the short-term average price
(50-day SMA) moves above the long-term average (200-day SMA), that's
called a "golden cross" and is often read as a bullish (positive) signal.
The opposite — 50-day SMA falling below the 200-day SMA — is called a
"death cross" and is often read as bearish (negative). These are
descriptive trend labels, not guarantees of future price movement.

**RSI (Relative Strength Index)** — A number from 0 to 100 that measures
how fast and how much a price has recently moved up versus down.
Traditionally, RSI above 70 is called "overbought" (may be due for a
pullback) and below 30 is called "oversold" (may be due for a bounce) —
but neither is a guarantee.

**Volatility** — How much a stock's price swings around, statistically.
Higher volatility means bigger, more frequent price moves (higher risk of
large gains or losses in a short time).

**Max Drawdown** — The biggest drop, in percentage terms, from a price
peak to the lowest point that followed it, within the period being
measured. A way to gauge "how bad could it have gotten" if you'd bought at
the worst possible time.

**Health Score** — This project's own transparent, rule-based 0-100 score
combining valuation, momentum, and profitability signals. It is *not* a
prediction of future returns — just a documented summary of current
conditions. See `docs/ARCHITECTURE.md` for the exact formula.

**Grounding (in AI)** — Constraining an AI model to only use information
it's explicitly given (in this case, the computed metrics/fundamentals),
rather than letting it rely on (potentially outdated or wrong) knowledge
from its training data.

**Hallucination (in AI)** — When an AI model states something as fact that
is actually made up or incorrect. In a finance context this is especially
risky (e.g. inventing a P/E ratio), which is why this project's prompts
explicitly instruct the model never to invent numbers not provided to it.

**TTL Cache (Time-To-Live Cache)** — A temporary storage layer that
remembers a recent answer (e.g. a stock's price data) for a set amount of
time (this project uses 5 minutes) so repeated requests don't have to
re-fetch from the original source every time.
