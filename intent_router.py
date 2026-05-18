"""
intent_router.py
────────────────
Classifies user intents BEFORE hitting the LLM to fetch context.
Categories: stock_price, commodity, investment, market_news, general.
"""

import re
from skills.stock_api import get_quote, get_news, extract_ticker

class IntentRouter:
    def __init__(self):
        pass

    def classify_and_contextualize(self, text: str) -> str:
        """
        Identify intent, fetch live data if needed, return formatted context.
        """
        text_lower = text.lower()
        context = ""

        # ── 1. Stock Price ──────────────────────────────────────────────────
        if any(w in text_lower for w in ["price of", "stock price", "quote for", "how is"]):
            ticker = extract_ticker(text)
            if ticker:
                quote = get_quote(ticker)
                if quote and not quote.get("error"):
                    direction = "up" if (quote.get("change", 0) or 0) >= 0 else "down"
                    context = (
                        f"LIVE STOCK DATA: {ticker} ({quote.get('name', ticker)}) "
                        f"Price: {quote['price']} {quote.get('currency','USD')} | "
                        f"Today: {direction} {quote.get('change_pct', 0)}%"
                    )

        # ── 2. Market News ──────────────────────────────────────────────────
        elif any(w in text_lower for w in ["market news", "stock news", "business news"]):
            ticker = extract_ticker(text)
            news = get_news(ticker, count=3) if ticker else get_news(None, count=3)
            if news:
                lines = ["RECENT HEADLINES:"]
                for n in news:
                    lines.append(f"- {n.get('headline')} ({n.get('sentiment')})")
                context = "\n".join(lines)

        # ── 3. Commodity / General Investment ───────────────────────────────
        commodity_words = ["gold", "silver", "crude", "oil", "platinum", "copper"]
        rate_words = ["rate", "price", "today", "current", "now", "how much", "worth", "trading"]
        
        has_commodity = any(c in text_lower for c in commodity_words)
        has_rate = any(r in text_lower for r in rate_words)
        
        if has_commodity and has_rate:
            commodity_map = {
                "gold": "GC=F",
                "silver": "SI=F",
                "crude": "CL=F",
                "oil": "CL=F",
                "platinum": "PL=F",
                "copper": "HG=F"
            }
            
            # Find which commodity was asked about
            detected_commodity = None
            for c in commodity_words:
                if c in text_lower:
                    detected_commodity = c
                    break
            
            if detected_commodity:
                ticker = commodity_map.get(detected_commodity)
                quote = get_quote(ticker)
                
                if quote and not quote.get("error"):
                    context = (
                        f"Live market data: {detected_commodity.upper()} is currently at "
                        f"{quote['price']} {quote.get('currency', 'USD')}."
                    )
                else:
                    context = (
                        f"Live fetch failed for {detected_commodity.upper()}. "
                        "Answer from general knowledge and clearly state data may not be current."
                    )

        return context
