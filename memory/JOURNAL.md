# Build Journal

Past-tense log of what actually happened while building Equity Research
Copilot, including network/tooling results and any dead ends. Written
after the fact based on the real commands run during the build.

## Environment check

- Confirmed Python 3.14.5 and pip 26.1.2 available on Windows.
- Confirmed Node v24 / npm 11.12.1 available.
- Ran a quick network smoke test before installing anything: `curl` to
  `pypi.org` returned HTTP 200 (PyPI reachable). `curl` to
  `query1.finance.yahoo.com` returned HTTP 429 (rate-limited) on the very
  first raw HTTP probe — a useful early signal that Yahoo's endpoints can
  throttle bare requests, even before yfinance's own session/header
  handling kicks in. This informed the decision to make every yfinance
  call in `market_data.py` defensively wrapped, since 429s are a real,
  observed failure mode in this environment, not a hypothetical.

## Backend dependency install

- Ran `pip install --user -r requirements.txt` (chose `--user` install
  over a venv, to keep the setup simple for a portfolio project running in
  a single sandboxed environment; documented here as the choice made).
- Install succeeded cleanly. Noted one incidental dependency conflict
  resolution: `google-generativeai`'s transitive dependency `protobuf`
  downgraded an already-installed `protobuf 7.35.1` to `5.29.6` — pip
  handled this automatically with no errors.

## yfinance real-network test

- After install, ran a direct Python check: `yf.Ticker('AAPL').history(period='1mo')`
  and `.info`. **This worked** — returned 21 rows of real OHLCV history and
  a populated `.info` dict (`trailingPE` = 37.99 at the time of the test).
  So despite the earlier raw-HTTP 429 on a bare curl probe, `yfinance`'s
  own request handling (session reuse, headers, `curl_cffi` backend)
  successfully fetched real data in this sandbox. This is documented in
  `docs/DEPLOYMENT.md` as a caveat: reliability can vary by request
  pattern, and defensive error handling remains necessary even when a
  manual test succeeds.
- Given real network access worked, `notebooks/01_metrics_validation.ipynb`
  was built using real AAPL/MSFT/GOOGL data (not synthetic placeholders),
  with actual computed output values transcribed from a real run of
  `api/analytics.py` functions.

## pytest results

- Wrote `tests/test_analytics.py` with fully synthetic, hand-constructed
  pandas fixtures (no network calls) covering SMA, golden cross, max
  drawdown, returns, RSI (including one hand-computed numeric example),
  volatility, and health-score boundary/clamping behavior.
- First run: **all 20 tests passed** on the first attempt (`pytest tests/ -v`
  → `20 passed in 1.03s`). No fixture or formula bugs needed fixing.

## FastAPI endpoint verification

- Started `uvicorn api.index:app --port 8000` from the project root and
  exercised all four endpoints with `curl`:
  - `GET /api/ticker/AAPL` → 200, 251 real price points, full metrics and
    fundamentals populated from real Yahoo data.
  - `GET /api/ticker/AAPL/peers?peers=MSFT,GOOGL` → 200, ratio table with
    real P/E, P/B, ROE, margin, market cap for all three tickers, and a
    computed health score of 77.4 for AAPL at the time of the test.
  - `POST /api/research-note` (no `GEMINI_API_KEY` set) → 200, rule-based
    templated text with all five required sections plus the disclaimer.
  - `POST /api/chat` (no key set) → 200, rule-based grounded reply text.
  - `GET /api/ticker/ZZZZZINVALIDTICKER123` → **clean 404 JSON**
    (`{"detail": "No price data found for ticker '...'. ..."}`), confirmed
    NOT a 500 stack trace, matching the spec requirement.
- One practical snag while testing on Windows/Git Bash: writing curl
  output to `/tmp/...` or to the tool's scratchpad path failed silently
  (`/tmp` doesn't exist on this Windows Git Bash setup, and Python opened
  with a POSIX-style scratchpad path couldn't resolve it either). Worked
  around this by writing curl output directly into the project directory
  as a temp file, reading it with Python, then deleting it — a minor
  Windows/Git-Bash path-translation quirk, not a bug in the app itself.

## Gemini no-key fallback verification

- Ran a standalone script calling `generate_research_note`, `chat`, and
  `explain_peer_comparison` directly, with `GEMINI_API_KEY` explicitly
  unset (`unset GEMINI_API_KEY` in the shell before running).
- All three functions returned **sensible templated text, no exceptions**,
  each correctly prefixed with "This is a rule-based summary — set
  GEMINI_API_KEY for AI-generated analysis." (the "not-configured" variant
  of the fallback message, as opposed to the "temporarily unavailable"
  variant used when a key IS set but the call itself fails) and each
  ending with the disclaimer line.

## Frontend scaffold

- Ran `npx create-next-app@latest app --typescript --tailwind --app
  --no-src-dir --import-alias "@/*" --eslint --use-npm --yes` from inside
  `equity-research-copilot/`. It succeeded but **also ran `git init`
  inside `app/`** as a side effect of create-next-app's default behavior —
  removed that nested `.git` directory immediately afterward, since the
  task constraints prohibit creating any git repos.
- `npx shadcn@latest init` had two rounds of interactive-prompt friction:
  1. `-b neutral` is not a valid enum value in this shadcn version (valid
     values are only `base` or `radix`) — had to drop that flag.
  2. Even with `-b base -y`, it still prompted interactively for a
     "preset" (Nova/Vega/Maia/...). Solved by using the `-d`/`--defaults`
     flag instead, which maps to `--template=next --preset=base-nova` and
     runs fully non-interactively.
  3. `shadcn add ... --force` failed with "unknown option '--force'" in
     this CLI version — dropped `--force` and reran `shadcn add` without
     it, which succeeded (it just skipped the one already-identical file,
     `button.tsx`, rather than erroring).
- This shadcn version generates components on top of **base-ui**
  (`@base-ui/react`), not Radix as in older shadcn docs/training data. Its
  `Trigger` components use a `render={<Component />}` prop instead of the
  Radix-style `asChild` boolean prop. This caused two real TypeScript
  build failures (`SheetTrigger asChild` and `TooltipTrigger asChild`),
  both fixed by switching to the `render` prop pattern. Also noticed the
  scaffolded project ships an `AGENTS.md` explicitly warning that this
  Next.js version has breaking API changes from training-data expectations
  — consistent with what was observed.
- `npm run build` (`next build`) hit one more real TypeScript error after
  the base-ui fixes: Recharts' `Tooltip formatter` prop's value type is
  `ValueType | undefined`, not `number | string` as initially typed —
  fixed by removing the explicit param type annotation and handling
  `undefined` at runtime instead.
- After those three fixes, `npm run build` succeeded with **zero errors**
  and `npm run lint` reported only 4 minor "unused variable" warnings
  (cleaned up), zero errors, on the final pass.
- Did a quick `npm run dev` + `curl localhost:3000/` sanity check: the dev
  server served real, correctly rendered HTML including the ticker search
  form, confirming the client-only-fetch architecture works even with no
  backend running (no build-time network calls were made, matching spec).
