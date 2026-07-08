"""
index.py — FastAPI application entrypoint for Equity Research Copilot.

Exposes:
  GET  /api/ticker/{symbol}
  GET  /api/ticker/{symbol}/peers?peers=A,B,C
  POST /api/research-note
  POST /api/chat

CORS is enabled for http://localhost:3000 (the Next.js dev server).
All yfinance failures are converted to clean 4xx JSON responses by
market_data.MarketDataError -> HTTPException, never a raw 500.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import analytics, gemini_client, market_data

app = FastAPI(title="Equity Research Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PricePoint(BaseModel):
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None


class TickerResponse(BaseModel):
    symbol: str
    prices: List[PricePoint]
    metrics: Dict[str, Any]
    fundamentals: Dict[str, Any]


class PeerRow(BaseModel):
    symbol: str
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    roe: Optional[float] = None
    profit_margin: Optional[float] = None
    market_cap: Optional[float] = None
    debt_to_equity: Optional[float] = None


class PeersResponse(BaseModel):
    symbol: str
    peers: List[str]
    ratio_table: List[PeerRow]
    health_score: Dict[str, Any]


class ResearchNoteRequest(BaseModel):
    symbol: str
    metrics: Optional[Dict[str, Any]] = None
    fundamentals: Optional[Dict[str, Any]] = None
    peers: Optional[List[Dict[str, Any]]] = None


class ResearchNoteResponse(BaseModel):
    text: str
    disclaimer: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    symbol: str
    metrics: Optional[Dict[str, Any]] = None
    history: Optional[List[ChatMessage]] = None
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _history_to_price_points(history) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for idx, row in history.iterrows():
        points.append({
            "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
            "open": float(row["Open"]) if "Open" in row and row["Open"] == row["Open"] else None,
            "high": float(row["High"]) if "High" in row and row["High"] == row["High"] else None,
            "low": float(row["Low"]) if "Low" in row and row["Low"] == row["Low"] else None,
            "close": float(row["Close"]) if "Close" in row and row["Close"] == row["Close"] else None,
            "volume": float(row["Volume"]) if "Volume" in row and row["Volume"] == row["Volume"] else None,
        })
    return points


def _fetch_symbol_bundle(symbol: str) -> Dict[str, Any]:
    """Fetch history + info, compute metrics + fundamentals. Raises
    HTTPException with a clean status code on any MarketDataError.
    """
    try:
        history = market_data.get_history(symbol, period="1y")
    except market_data.MarketDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    metrics = analytics.compute_price_metrics(history)

    try:
        info = market_data.get_info(symbol)
        fundamentals = analytics.extract_fundamentals(info)
    except market_data.MarketDataError:
        # Fundamentals are best-effort; price data alone is still useful.
        fundamentals = analytics.extract_fundamentals(None)

    return {"history": history, "metrics": metrics, "fundamentals": fundamentals}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ticker/{symbol}", response_model=TickerResponse)
def get_ticker(symbol: str) -> Any:
    bundle = _fetch_symbol_bundle(symbol)
    prices = _history_to_price_points(bundle["history"])
    return {
        "symbol": symbol.strip().upper(),
        "prices": prices,
        "metrics": bundle["metrics"],
        "fundamentals": bundle["fundamentals"],
    }


@app.get("/api/ticker/{symbol}/peers", response_model=PeersResponse)
def get_peers(symbol: str, peers: Optional[str] = Query(default=None)) -> Any:
    bundle = _fetch_symbol_bundle(symbol)
    fundamentals = bundle["fundamentals"]
    metrics = bundle["metrics"]

    explicit_peers = [p for p in (peers.split(",") if peers else []) if p.strip()]
    resolved_peers = analytics.resolve_peers(fundamentals.get("sector"), explicit_peers)

    rows: List[Dict[str, Any]] = [{"symbol": symbol.strip().upper(), "fundamentals": fundamentals}]
    for peer_symbol in resolved_peers:
        try:
            peer_info = market_data.get_info(peer_symbol)
            peer_fundamentals = analytics.extract_fundamentals(peer_info)
        except market_data.MarketDataError:
            peer_fundamentals = analytics.extract_fundamentals(None)
        rows.append({"symbol": peer_symbol, "fundamentals": peer_fundamentals})

    ratio_table = analytics.build_ratio_table(rows)

    peer_pes = [row["trailing_pe"] for row in ratio_table[1:]]
    health_score = analytics.compute_health_score(
        target_pe=fundamentals.get("trailing_pe"),
        peer_pes=peer_pes,
        last_close=metrics.get("last_close"),
        sma_50=metrics.get("sma_50"),
        sma_200=metrics.get("sma_200"),
        rsi_14=metrics.get("rsi_14"),
        profit_margin=fundamentals.get("profit_margin"),
        roe=fundamentals.get("roe"),
    )

    return {
        "symbol": symbol.strip().upper(),
        "peers": resolved_peers,
        "ratio_table": ratio_table,
        "health_score": health_score,
    }


@app.post("/api/research-note", response_model=ResearchNoteResponse)
def post_research_note(body: ResearchNoteRequest) -> Any:
    metrics = body.metrics
    fundamentals = body.fundamentals
    peers = body.peers

    if metrics is None or fundamentals is None:
        bundle = _fetch_symbol_bundle(body.symbol)
        metrics = metrics or bundle["metrics"]
        fundamentals = fundamentals or bundle["fundamentals"]

    result = gemini_client.generate_research_note(
        ticker=body.symbol,
        metrics=metrics,
        fundamentals=fundamentals,
        peers=peers or [],
    )
    return result


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> Any:
    history = [turn.model_dump() for turn in (body.history or [])]
    result = gemini_client.chat(
        ticker=body.symbol,
        metrics=body.metrics or {},
        history=history,
        user_message=body.message,
    )
    return result
