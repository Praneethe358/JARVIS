"""
skills/stock_api.py
───────────────────
Stock data fetching layer for the NEXUS Stock Market Intelligence Module.

Data sources (in priority order):
  1. Alpha Vantage — live quotes, news (25 calls/day free)
  2. yfinance      — live quotes fallback (unlimited, no API key)
  3. Finnhub       — market news (60 calls/min free)

All responses are cached for 5 minutes (configurable via config.json:
  stock_cache_ttl_seconds) to stay within free tier limits.

Supports both Indian stocks (NSE: RELIANCE.NS) and US stocks (AAPL).
"""

import json
import time
import re
import urllib.request
import urllib.error
from datetime import datetime
from core.logger import log

# ── Cache store ────────────────────────────────────────────────────────────────
_cache: dict = {}   # { "cache_key": {"data": ..., "ts": float} }


def _cache_get(key: str, ttl: int = 300):
    """Return cached data if within TTL, else None."""
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < ttl:
        return entry["data"]
    return None


def _cache_set(key: str, data):
    """Store data in cache with current timestamp."""
    _cache[key] = {"data": data, "ts": time.time()}


def _http_get(url: str, headers: dict = None, timeout: int = 10) -> dict | list | None:
    """
    Simple HTTP GET using urllib. Returns parsed JSON or None on error.
    No third-party requests lib — consistent with NEXUS's urllib policy.
    """
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.warning(f"[StockAPI] HTTP {e.code} for {url}")
        return None
    except Exception as e:
        log.warning(f"[StockAPI] Request failed for {url}: {e}")
        return None


def _get_config():
    from core.config import CONFIG
    return CONFIG


# ── Quote fetching ─────────────────────────────────────────────────────────────

def get_quote(ticker: str) -> dict:
    """
    Fetch live stock quote. Returns dict with keys:
      ticker, price, change, change_pct, prev_close, volume,
      high, low, name, currency, cached (bool), error (str or None)

    Tries Alpha Vantage first, falls back to yfinance.
    Supports Indian tickers: pass 'RELIANCE.NS' or just 'RELIANCE' for NSE.
    """
    ticker = ticker.upper().strip()
    cache_key = f"quote:{ticker}"
    cfg = _get_config()
    ttl = cfg.get("stock_cache_ttl_seconds", 300)

    cached = _cache_get(cache_key, ttl)
    if cached:
        cached["cached"] = True
        return cached

    result = _quote_alpha_vantage(ticker, cfg) or _quote_yfinance(ticker)

    if result:
        result["cached"] = False
        _cache_set(cache_key, result)
        return result

    return {
        "ticker": ticker, "price": None, "change": None, "change_pct": None,
        "prev_close": None, "volume": None, "high": None, "low": None,
        "name": ticker, "currency": "USD", "cached": False,
        "error": "Could not fetch quote. Check ticker symbol or API key."
    }


def _quote_alpha_vantage(ticker: str, cfg: dict) -> dict | None:
    """Fetch from Alpha Vantage GLOBAL_QUOTE endpoint."""
    api_key = cfg.get("alpha_vantage_api_key", "")
    if not api_key or api_key.startswith("GET_FREE_KEY"):
        return None

    # Alpha Vantage uses BSE/NSE tickers natively (e.g., RELIANCE.BSE)
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
    )
    data = _http_get(url)
    if not data:
        return None

    q = data.get("Global Quote", {})
    if not q or not q.get("05. price"):
        # Alpha Vantage returns empty dict on invalid ticker
        log.warning(f"[StockAPI] Alpha Vantage: no data for {ticker}")
        return None

    try:
        price      = float(q.get("05. price", 0))
        change     = float(q.get("09. change", 0))
        change_pct = q.get("10. change percent", "0%").replace("%", "")
        change_pct = float(change_pct)
        prev_close = float(q.get("08. previous close", 0))
        volume     = int(q.get("06. volume", 0))
        high       = float(q.get("03. high", 0))
        low        = float(q.get("04. low", 0))
        return {
            "ticker": ticker, "price": price, "change": change,
            "change_pct": change_pct, "prev_close": prev_close,
            "volume": volume, "high": high, "low": low,
            "name": ticker, "currency": "USD", "error": None,
            "source": "Alpha Vantage",
        }
    except (ValueError, KeyError) as e:
        log.warning(f"[StockAPI] Alpha Vantage parse error for {ticker}: {e}")
        return None


def _quote_yfinance(ticker: str) -> dict | None:
    """
    Fetch from Yahoo Finance using yfinance library.
    Falls back gracefully if yfinance is not installed.
    Automatically appends '.NS' for Indian tickers without exchange suffix.
    """
    try:
        import yfinance as yf
    except ImportError:
        log.warning("[StockAPI] yfinance not installed. Run: pip install yfinance")
        return None

    try:
        # Auto-detect Indian tickers (no dot in ticker = might be NSE)
        symbol = ticker
        info = yf.Ticker(symbol).fast_info
        price = getattr(info, "last_price", None)

        if price is None and "." not in ticker:
            # Try NSE suffix
            symbol = ticker + ".NS"
            info = yf.Ticker(symbol).fast_info
            price = getattr(info, "last_price", None)

        if price is None:
            return None

        prev_close  = getattr(info, "previous_close", price)
        change      = round(price - prev_close, 2)
        change_pct  = round((change / prev_close * 100) if prev_close else 0, 2)
        volume      = getattr(info, "three_month_average_volume", 0)
        high        = getattr(info, "day_high", price)
        low         = getattr(info, "day_low", price)
        currency    = getattr(info, "currency", "USD")

        # Get company name
        try:
            name = yf.Ticker(symbol).info.get("shortName", symbol)
        except Exception:
            name = symbol

        return {
            "ticker": symbol, "price": round(price, 2), "change": change,
            "change_pct": change_pct, "prev_close": round(prev_close, 2),
            "volume": int(volume) if volume else 0,
            "high": round(high, 2), "low": round(low, 2),
            "name": name, "currency": currency, "error": None,
            "source": "Yahoo Finance",
        }
    except Exception as e:
        log.warning(f"[StockAPI] yfinance error for {ticker}: {e}")
        return None


# ── News fetching ──────────────────────────────────────────────────────────────

def get_news(ticker: str = None, count: int = 5) -> list[dict]:
    """
    Fetch financial news articles. Returns list of dicts:
      { headline, source, time, url, sentiment, ticker }

    Uses Finnhub (primary) or Alpha Vantage NEWS (secondary).
    Sentiment is tagged by AI (via stock_analyst) — defaults to "Neutral" here.
    """
    cache_key = f"news:{ticker or 'market'}"
    cfg = _get_config()
    ttl = cfg.get("stock_cache_ttl_seconds", 300)

    cached = _cache_get(cache_key, ttl)
    if cached:
        return cached

    articles = _news_finnhub(ticker, count, cfg) or _news_alpha_vantage(ticker, count, cfg)

    if articles is None:
        articles = [{
            "headline": "Market news unavailable — check API keys",
            "source": "NEXUS", "time": _now_str(), "url": "",
            "sentiment": "Neutral", "ticker": ticker or "MARKET",
        }]

    _cache_set(cache_key, articles)
    return articles


def _news_finnhub(ticker: str | None, count: int, cfg: dict) -> list[dict] | None:
    """Fetch from Finnhub /news or /company-news."""
    api_key = cfg.get("finnhub_api_key", "")
    if not api_key or api_key.startswith("GET_FREE_KEY"):
        return None

    if ticker:
        # Company-specific news: last 7 days
        from_date = datetime.now().strftime("%Y-%m-%d")
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={ticker}&from=2024-01-01&to={from_date}&token={api_key}"
        )
    else:
        url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"

    data = _http_get(url)
    if not data or not isinstance(data, list):
        return None

    articles = []
    for item in data[:count]:
        articles.append({
            "headline": item.get("headline", "No headline"),
            "source"  : item.get("source", "Finnhub"),
            "time"    : _ts_to_str(item.get("datetime", 0)),
            "url"     : item.get("url", ""),
            "sentiment": "Neutral",   # will be AI-tagged by stock_analyst
            "ticker"  : ticker or "MARKET",
        })
    return articles if articles else None


def _news_alpha_vantage(ticker: str | None, count: int, cfg: dict) -> list[dict] | None:
    """Fetch from Alpha Vantage NEWS_SENTIMENT endpoint."""
    api_key = cfg.get("alpha_vantage_api_key", "")
    if not api_key or api_key.startswith("GET_FREE_KEY"):
        return None

    tickers_param = f"&tickers={ticker}" if ticker else ""
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=NEWS_SENTIMENT{tickers_param}"
        f"&limit={count}&apikey={api_key}"
    )
    data = _http_get(url)
    if not data:
        return None

    feed = data.get("feed", [])
    if not feed:
        return None

    articles = []
    for item in feed[:count]:
        # Alpha Vantage provides sentiment scores
        overall = item.get("overall_sentiment_label", "Neutral")
        sentiment = _map_av_sentiment(overall)
        articles.append({
            "headline": item.get("title", "No headline"),
            "source"  : item.get("source", "Alpha Vantage"),
            "time"    : _parse_av_time(item.get("time_published", "")),
            "url"     : item.get("url", ""),
            "sentiment": sentiment,
            "ticker"  : ticker or "MARKET",
        })
    return articles if articles else None


def _map_av_sentiment(label: str) -> str:
    """Map Alpha Vantage sentiment labels to Bullish/Bearish/Neutral."""
    label = label.lower()
    if "bullish" in label or "positive" in label or "somewhat_bullish" in label:
        return "Bullish"
    if "bearish" in label or "negative" in label or "somewhat_bearish" in label:
        return "Bearish"
    return "Neutral"


# ── Ticker extraction from natural language ────────────────────────────────────

# Common Indian and US ticker mappings for voice commands
_TICKER_MAP = {
    # Indian
    "reliance": "RELIANCE.NS",  "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",            "tata consultancy": "TCS.NS",
    "infosys": "INFY.NS",       "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS",
    "wipro": "WIPRO.NS",        "bajaj finance": "BAJFINANCE.NS",
    "tatasteel": "TATASTEEL.NS", "tata steel": "TATASTEEL.NS",
    "itc": "ITC.NS",            "asian paints": "ASIANPAINT.NS",
    "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS",
    "maruti": "MARUTI.NS",      "sunpharma": "SUNPHARMA.NS",
    # US
    "apple": "AAPL",    "tesla": "TSLA",    "amazon": "AMZN",
    "google": "GOOGL",  "alphabet": "GOOGL", "microsoft": "MSFT",
    "nvidia": "NVDA",   "meta": "META",      "netflix": "NFLX",
}


def extract_ticker(text: str) -> str | None:
    """
    Extract a stock ticker from natural language text.
    Tries known name→ticker mappings first, then looks for uppercase words.
    """
    text_lower = text.lower()
    for name, ticker in _TICKER_MAP.items():
        if name in text_lower:
            return ticker

    # Look for explicit ticker patterns: 2-5 uppercase letters optionally followed by .NS/.BSE
    match = re.search(r'\b([A-Z]{2,5}(?:\.(?:NS|BSE|BO))?)\b', text)
    if match:
        return match.group(1)

    return None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now().strftime("%H:%M %d %b")


def _ts_to_str(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%H:%M %d %b")
    except Exception:
        return _now_str()


def _parse_av_time(s: str) -> str:
    # Alpha Vantage format: 20240518T143000
    try:
        dt = datetime.strptime(s, "%Y%m%dT%H%M%S")
        return dt.strftime("%H:%M %d %b")
    except Exception:
        return _now_str()
