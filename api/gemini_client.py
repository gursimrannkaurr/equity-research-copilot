"""
gemini_client.py — Gemini 2.5 Flash wrapper for grounded research notes,
chat Q&A, and peer comparison explanations.

ZERO-COST + GRACEFUL DEGRADATION DESIGN:
- Uses Google's free-tier "gemini-2.5-flash" model via `google-generativeai`.
- Reads GEMINI_API_KEY from the environment. If it is not set, every public
  function in this module falls back to a templated, rule-based text
  response built from the same metrics — it NEVER raises.
- Any exception during an actual Gemini call (network error, rate limit,
  auth failure, etc.) is caught and we fall back to the same templated
  text, prefixed with a notice that the AI analyst is temporarily
  unavailable.
- All prompts explicitly instruct the model: "Only use the numbers
  provided below. Never invent or estimate financial figures not given to
  you. If information is missing, say so explicitly." This is the
  anti-hallucination "grounding" strategy documented in
  docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional

DISCLAIMER = "Educational project. Not investment advice."

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are an equity research assistant embedded in a portfolio project. "
    "Only use the numbers provided below. Never invent or estimate financial "
    "figures not given to you. If information is missing, say so explicitly. "
    "Always keep a neutral, educational tone. Never phrase output as personalized "
    "investment advice."
)


def _get_model():
    """Return a configured genai.GenerativeModel, or None if no API key is
    set or the SDK/model cannot be initialized. Never raises.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        return model
    except Exception:
        return None


def _fmt(value: Any, suffix: str = "", pct: bool = False, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    try:
        if pct:
            return f"{value * 100:.{digits}f}%"
        return f"{value:.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def _serialize_context(ticker: str, metrics: Optional[Dict[str, Any]],
                        fundamentals: Optional[Dict[str, Any]],
                        peers: Optional[List[Dict[str, Any]]]) -> str:
    """Serialize all computed data into a structured JSON block that gets
    injected verbatim into the Gemini prompt. This IS the grounding: the
    model is given no other numeric source of truth.
    """
    payload = {
        "ticker": ticker,
        "metrics": metrics or {},
        "fundamentals": fundamentals or {},
        "peers": peers or [],
    }
    return json.dumps(payload, indent=2, default=str)


# ---------------------------------------------------------------------------
# Rule-based fallback templates
# ---------------------------------------------------------------------------

def _fallback_research_note(ticker: str, metrics: Dict[str, Any], fundamentals: Dict[str, Any],
                             peers: List[Dict[str, Any]], unavailable_notice: bool = False) -> str:
    pe = fundamentals.get("trailing_pe")
    peer_pes = [p.get("trailing_pe") for p in peers if p.get("trailing_pe")]
    peer_avg_pe = sum(peer_pes) / len(peer_pes) if peer_pes else None

    valuation_line = "No peer P/E data available to compare." if peer_avg_pe is None or pe is None else (
        f"P/E of {pe:.2f} is " + ("above" if pe > peer_avg_pe else "below") +
        f" the peer average of {peer_avg_pe:.2f}."
    )

    sma_50 = metrics.get("sma_50")
    sma_200 = metrics.get("sma_200")
    last_close = metrics.get("last_close")
    if last_close is not None and sma_50 is not None and sma_200 is not None:
        trend = "above both its 50-day and 200-day moving averages (bullish trend)" if last_close > sma_50 and last_close > sma_200 \
            else "below both its 50-day and 200-day moving averages (bearish trend)" if last_close < sma_50 and last_close < sma_200 \
            else "mixed relative to its 50-day and 200-day moving averages"
        momentum_line = f"Price is currently {trend}."
    else:
        momentum_line = "Insufficient moving-average data to characterize trend."

    rsi = metrics.get("rsi_14")
    rsi_line = "RSI(14) unavailable." if rsi is None else (
        f"RSI(14) is {rsi:.1f}, which is " +
        ("oversold territory." if rsi < 30 else "overbought territory." if rsi > 70 else "in a neutral range.")
    )

    header = ""
    if unavailable_notice:
        header = "AI analyst is temporarily unavailable, showing rule-based summary.\n\n"
    else:
        header = "This is a rule-based summary — set GEMINI_API_KEY for AI-generated analysis.\n\n"

    return (
        f"{header}"
        f"## Business Snapshot\n"
        f"{fundamentals.get('short_name') or ticker} ({ticker}) — sector: {fundamentals.get('sector') or 'N/A'}, "
        f"industry: {fundamentals.get('industry') or 'N/A'}. Market cap: {_fmt(fundamentals.get('market_cap'))}.\n\n"
        f"## Valuation View\n{valuation_line}\n\n"
        f"## Momentum / Technicals\n{momentum_line} {rsi_line}\n\n"
        f"## Risks\n"
        f"This summary is generated from a limited set of computed metrics and public fundamentals data; "
        f"it does not account for qualitative factors, recent news, or forward guidance.\n\n"
        f"## Questions for Further Research\n"
        f"- What are the company's most recent quarterly earnings trends?\n"
        f"- How does the competitive landscape compare across the peer set?\n"
        f"- What macro or sector-specific risks could affect forward estimates?\n\n"
        f"{DISCLAIMER}"
    )


def _fallback_chat_reply(ticker: str, metrics: Dict[str, Any], user_message: str, unavailable_notice: bool = False) -> str:
    header = ("AI analyst is temporarily unavailable, showing rule-based summary. "
              if unavailable_notice else
              "This is a rule-based reply — set GEMINI_API_KEY for AI-generated chat. ")
    known = {k: v for k, v in metrics.items() if v is not None}
    if not known:
        body = f"No computed metrics are currently available for {ticker} to answer: \"{user_message}\""
    else:
        parts = ", ".join(f"{k}={v}" for k, v in list(known.items())[:6])
        body = (
            f"Based on the currently computed metrics for {ticker} ({parts}), "
            f"I can't generate a free-form AI answer right now, but the numbers above are the "
            f"grounded data available to answer: \"{user_message}\""
        )
    return f"{header}{body}\n\n{DISCLAIMER}"


def _fallback_peer_explanation(ratio_table: List[Dict[str, Any]], unavailable_notice: bool = False) -> str:
    header = ("AI analyst is temporarily unavailable, showing rule-based summary. "
              if unavailable_notice else
              "This is a rule-based summary — set GEMINI_API_KEY for AI-generated analysis. ")
    if not ratio_table:
        return f"{header}No peer comparison data was provided.\n\n{DISCLAIMER}"

    pes = [(row.get("symbol"), row.get("trailing_pe")) for row in ratio_table if row.get("trailing_pe")]
    if pes:
        cheapest = min(pes, key=lambda x: x[1])
        priciest = max(pes, key=lambda x: x[1])
        pe_line = (f"Among the compared companies, {cheapest[0]} trades at the lowest P/E ({cheapest[1]:.2f}) "
                   f"and {priciest[0]} at the highest ({priciest[1]:.2f}).")
    else:
        pe_line = "P/E data was not available for the compared companies."

    roes = [(row.get("symbol"), row.get("roe")) for row in ratio_table if row.get("roe") is not None]
    if roes:
        best_roe = max(roes, key=lambda x: x[1])
        roe_line = f"{best_roe[0]} shows the strongest return on equity in this set at {best_roe[1]*100:.1f}%."
    else:
        roe_line = "Return on equity data was not available for the compared companies."

    return f"{header}{pe_line} {roe_line}\n\n{DISCLAIMER}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_research_note(ticker: str, metrics: Optional[Dict[str, Any]] = None,
                            fundamentals: Optional[Dict[str, Any]] = None,
                            peers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
    """Generate a structured research note with sections: Business Snapshot,
    Valuation View, Momentum/Technicals, Risks, Questions for Further
    Research. Always appends the hardcoded disclaimer, regardless of
    whether the text came from Gemini or the rule-based fallback.

    Returns {"text": str, "disclaimer": str}.
    """
    metrics = metrics or {}
    fundamentals = fundamentals or {}
    peers = peers or []

    model = _get_model()
    if model is None:
        text = _fallback_research_note(ticker, metrics, fundamentals, peers, unavailable_notice=False)
        return {"text": text, "disclaimer": DISCLAIMER}

    context_block = _serialize_context(ticker, metrics, fundamentals, peers)
    prompt = (
        f"Using ONLY the structured data below for ticker {ticker}, write a research note with these "
        f"exact section headers: '## Business Snapshot', '## Valuation View', '## Momentum/Technicals', "
        f"'## Risks', '## Questions for Further Research'. Be concise (2-4 sentences per section). "
        f"If a needed number is missing/null, explicitly say so instead of guessing.\n\n"
        f"DATA:\n{context_block}"
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
        if DISCLAIMER not in text:
            text = f"{text}\n\n{DISCLAIMER}"
        return {"text": text, "disclaimer": DISCLAIMER}
    except Exception:
        text = _fallback_research_note(ticker, metrics, fundamentals, peers, unavailable_notice=True)
        return {"text": text, "disclaimer": DISCLAIMER}


def chat(ticker: str, metrics: Optional[Dict[str, Any]], history: Optional[List[Dict[str, str]]],
         user_message: str) -> Dict[str, str]:
    """Stateless follow-up Q&A grounded in the same metrics dict passed by
    the frontend on every call (no server-side session state / DB).

    `history` is a list of {"role": "user"|"assistant", "content": str}
    dicts, resent by the client on every call.

    Returns {"reply": str}.
    """
    metrics = metrics or {}
    history = history or []

    model = _get_model()
    if model is None:
        reply = _fallback_chat_reply(ticker, metrics, user_message, unavailable_notice=False)
        return {"reply": reply}

    context_block = _serialize_context(ticker, metrics, None, None)
    convo_lines = []
    for turn in history[-10:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        convo_lines.append(f"{role}: {content}")
    convo_block = "\n".join(convo_lines) if convo_lines else "(no prior turns)"

    prompt = (
        f"You are answering a follow-up question about ticker {ticker}. Only use the DATA block below; "
        f"never invent numbers. If the answer requires data not present, say so explicitly.\n\n"
        f"DATA:\n{context_block}\n\n"
        f"Conversation so far:\n{convo_block}\n\n"
        f"User's new question: {user_message}\n"
        f"Answer concisely."
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
        if DISCLAIMER not in text:
            text = f"{text}\n\n{DISCLAIMER}"
        return {"reply": text}
    except Exception:
        reply = _fallback_chat_reply(ticker, metrics, user_message, unavailable_notice=True)
        return {"reply": reply}


def explain_peer_comparison(ratio_table: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
    """Plain-language paragraph explaining a peer ratio comparison table.

    Returns {"text": str, "disclaimer": str}.
    """
    ratio_table = ratio_table or []

    model = _get_model()
    if model is None:
        text = _fallback_peer_explanation(ratio_table, unavailable_notice=False)
        return {"text": text, "disclaimer": DISCLAIMER}

    context_block = json.dumps(ratio_table, indent=2, default=str)
    prompt = (
        f"Using ONLY the peer comparison table below, write a short plain-language paragraph (3-5 sentences) "
        f"summarizing the relative valuation and profitability picture. Never invent numbers not in the table. "
        f"If a field is missing/null for a company, mention that briefly rather than guessing.\n\n"
        f"DATA:\n{context_block}"
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
        if DISCLAIMER not in text:
            text = f"{text}\n\n{DISCLAIMER}"
        return {"text": text, "disclaimer": DISCLAIMER}
    except Exception:
        text = _fallback_peer_explanation(ratio_table, unavailable_notice=True)
        return {"text": text, "disclaimer": DISCLAIMER}
