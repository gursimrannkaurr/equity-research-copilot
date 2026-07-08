# Deployment (Vercel)

This project deploys as a **hybrid Vercel project**: a Python serverless
function (`api/index.py`, FastAPI via `@vercel/python`) alongside the
Next.js frontend (`app/`, via `@vercel/next`), wired together by
`vercel.json` at the repo root.

## Steps

1. **Push the repo to GitHub** (or your git provider of choice) and import
   it into Vercel ("Add New Project" → select the repo).
2. Vercel will detect `vercel.json` at the root. Confirm the build picks up
   both builds (`api/index.py` and `app/package.json`).
3. **Set the root-level environment variables** (Project Settings →
   Environment Variables):
   - `GEMINI_API_KEY` — optional. Without it, the app runs fully
     functional with rule-based summaries instead of AI-generated ones.
   - `NEXT_PUBLIC_API_BASE` — set this to your deployed domain's `/api`
     origin (e.g. `https://your-project.vercel.app`) so the frontend calls
     the same-origin serverless function instead of `localhost:8000`.
4. Deploy. Vercel builds the Next.js app as normal and deploys
   `api/index.py` as a Python serverless function reachable at `/api/*`
   per the `routes` rewrite in `vercel.json`.

## Getting a free `GEMINI_API_KEY`

1. Go to [aistudio.google.com](https://aistudio.google.com).
2. Sign in with a Google account.
3. Click "Get API key" → "Create API key" (a free-tier key is issued with
   no billing setup required for `gemini-2.5-flash` at low usage).
4. Copy the key into Vercel's environment variables as `GEMINI_API_KEY`
   (and/or your local `.env` file, based on `.env.example`).
5. Redeploy (or restart `uvicorn` locally) so the new env var is picked up.

Google's free tier has request-per-minute and daily quotas that can change;
if you exceed them, `gemini_client.py` will catch the resulting exception
and fall back to the rule-based summary automatically — the app keeps
working either way.

## `yfinance` reliability caveats on serverless

- **Cold starts**: a serverless function has no persistent process, so the
  in-process TTL cache in `market_data.py` (see below) is empty on every
  cold start — the first request after a period of inactivity always hits
  Yahoo Finance directly.
- **Datacenter IP throttling**: Yahoo Finance is more likely to rate-limit
  or block requests coming from cloud/datacenter IP ranges (which is what
  Vercel's serverless functions use) than from a typical residential IP.
  In practice this means `yfinance` calls can intermittently return 429s
  or empty data in production even when they work fine locally. The app is
  designed to degrade gracefully in this case — `market_data.py` converts
  any yfinance failure into a clean 404/502 JSON error (never a 500), and
  the frontend surfaces that error message rather than crashing.
- If Yahoo throttling becomes a persistent problem in a real deployment,
  the standard mitigations (not implemented here, to keep the project
  zero-cost) would be: a paid data provider with an SLA, a caching/proxy
  layer with a larger TTL, or self-hosting outside of Vercel's shared IP
  ranges.

## In-memory cache tradeoff

`api/market_data.py` uses a plain Python dict as an in-process cache with a
300-second TTL. This is intentionally simple and free (see
`memory/DECISIONS.md`), but has one important consequence on serverless:
**the cache resets on every cold start** and is not shared across
concurrent function instances. This is a **documented limitation, not a
bug** — for a portfolio/education project with light traffic, the
simplicity is worth the tradeoff. A production system would use a shared
cache (e.g. Vercel KV / Upstash Redis) to get consistent TTL behavior
across instances and warm starts.
