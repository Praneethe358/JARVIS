"""
skills/stock_analyst.py
────────────────────────
AI-powered market analyst using OpenRouter (DeepSeek-R1).

Automatically fetches relevant stock data (price, change, news) and injects
it as structured context into the OpenRouter prompt before answering.

System prompt: "You are a sharp financial analyst AI inside Nexus dashboard.
  Given live stock data, answer concisely with insight and confidence."

Responses are cached per (ticker + question_hash) for 5 minutes.
"""

import hashlib
import time
from core.logger import log

_ANALYST_SYSTEM_PROMPT = (
    "You are a sharp financial analyst AI inside Nexus dashboard. "
    "Given live stock data, answer concisely with insight and confidence. "
    "Keep answers under 4 sentences. Avoid markdown, bullet points, or symbols "
    "since your response will be spoken aloud."
)

# Simple cache: {hash → (response, timestamp)}
_analyst_cache: dict = {}
_CACHE_TTL = 300   # 5 minutes


def analyze(question: str, ticker: str = None) -> str:
    """
    Answer a market analysis question using OpenRouter with live data context.

    Args:
        question : Natural language question from the user.
        ticker   : Optional ticker to fetch data for. If None, attempts to
                   extract one from the question using stock_api.extract_ticker().

    Returns TTS-ready string.
    """
    from core.brain import Brain
    from skills.stock_api import get_quote, get_news, extract_ticker

    # ── Extract ticker if not provided ─────────────────────────────────────────
    if not ticker:
        ticker = extract_ticker(question)

    # ── Build context block ────────────────────────────────────────────────────
    context_lines = []

    if ticker:
        quote = get_quote(ticker)
        if quote.get("price") is not None:
            direction = "up" if (quote.get("change", 0) or 0) >= 0 else "down"
            cached_tag = " [cached]" if quote.get("cached") else ""
            context_lines.append(
                f"Stock Data{cached_tag}: {ticker} ({quote.get('name', ticker)}) "
                f"Price: {quote['price']} {quote.get('currency','USD')} | "
                f"Day Change: {quote.get('change', 'N/A')} ({quote.get('change_pct', 'N/A')}%) | "
                f"Today: {direction} | High: {quote.get('high','N/A')} Low: {quote.get('low','N/A')}"
            )
        else:
            context_lines.append(f"Stock Data: Could not fetch live data for {ticker}.")

        # Add recent headlines for context
        news = get_news(ticker, count=3)
        if news:
            context_lines.append("Recent Headlines:")
            for article in news:
                context_lines.append(
                    f"  [{article.get('sentiment','?')}] {article.get('headline','')}"
                    f" — {article.get('source','')} ({article.get('time','')})"
                )

    context_block = "\n".join(context_lines)

    # ── Build full prompt ───────────────────────────────────────────────────────
    if context_block:
        full_prompt = (
            f"[LIVE MARKET DATA]\n{context_block}\n\n"
            f"[USER QUESTION]\n{question}"
        )
    else:
        full_prompt = question

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = hashlib.md5(full_prompt.encode()).hexdigest()
    cached_entry = _analyst_cache.get(cache_key)
    if cached_entry and (time.time() - cached_entry[1]) < _CACHE_TTL:
        log.info("[StockAnalyst] Returning cached analysis.")
        return cached_entry[0]

    # ── Call OpenRouter ────────────────────────────────────────────────────────
    log.info(f"[StockAnalyst] Querying OpenRouter for: {question[:60]}...")
    brain = Brain()
    response = brain.ask_ai(
        full_prompt,
        system_prompt=_ANALYST_SYSTEM_PROMPT,
        use_cache=False   # we manage our own cache
    )

    if not response:
        if ticker:
            return (
                f"I couldn't get an analysis for {ticker} right now. "
                "Check your OpenRouter API key or try again later."
            )
        return "I couldn't reach the reasoning core. Check your OpenRouter API key."

    # ── Cache result ───────────────────────────────────────────────────────────
    _analyst_cache[cache_key] = (response, time.time())
    return response


def tag_news_sentiment(headline: str) -> str:
    """
    Use OpenRouter to tag a news headline as Bullish, Bearish, or Neutral.
    Uses a very short prompt to conserve API quota.
    Returns one of: "Bullish" | "Bearish" | "Neutral"
    """
    from core.brain import Brain

    cache_key = hashlib.md5(headline.encode()).hexdigest()
    cached_entry = _analyst_cache.get(f"sent:{cache_key}")
    if cached_entry and (time.time() - cached_entry[1]) < _CACHE_TTL:
        return cached_entry[0]

    brain = Brain()
    prompt = (
        f'Classify this financial news headline as exactly one word: '
        f'Bullish, Bearish, or Neutral.\nHeadline: "{headline}"\nAnswer:'
    )
    system = (
        "You classify financial news sentiment. "
        "Respond with exactly one word: Bullish, Bearish, or Neutral."
    )
    raw = brain.ask_ai(prompt, system_prompt=system, use_cache=False)

    # Extract the sentiment word robustly
    sentiment = "Neutral"
    if raw:
        raw_lower = raw.lower().strip()
        if "bullish" in raw_lower:
            sentiment = "Bullish"
        elif "bearish" in raw_lower:
            sentiment = "Bearish"

    _analyst_cache[f"sent:{cache_key}"] = (sentiment, time.time())
    return sentiment
