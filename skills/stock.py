"""
skills/stock.py
────────────────
NEXUS Stock Market Intelligence — main skill dispatcher.

Triggers: stock, market, portfolio, watchlist, price of, shares, invest,
          financial, buy shares, sell shares, p&l, profit, loss, holding,
          analyze stock, market news, stock news, set alert, add to watchlist.

Sub-dispatches to four modules:
  ① Portfolio   — P&L tracking, add/remove holdings
  ② AI Analyst  — OpenRouter-powered market Q&A
  ③ News        — Finnhub / Alpha Vantage headlines with sentiment
  ④ Watchlist   — Price alert tracking
"""

import re
from core.logger import log


class StockSkill:
    triggers = [
        # Portfolio
        "portfolio", "my portfolio", "p&l", "profit loss", "holdings",
        "add shares", "buy shares", "i bought", "i own",
        # Quotes
        "stock price", "price of", "share price", "quote", "how is",
        "market cap",
        # Analysis
        "analyze", "analyse", "should i buy", "should i hold", "should i sell",
        "why is", "why did", "market outlook", "stock analysis",
        # News
        "market news", "financial news", "stock news", "business news",
        # Watchlist
        "watchlist", "add to watchlist", "watch", "set alert", "alert when",
        "track stock", "notify me",
        # Generic market words
        "stock", "shares", "invest", "nse", "bse", "nifty", "sensex",
        "nasdaq", "dow jones", "s&p",
    ]

    # ── Public interface ───────────────────────────────────────────────────────

    def handle(self, command: str) -> str:
        """Dispatch to the appropriate sub-module based on command intent."""
        cmd = command.lower().strip()
        log.info(f"[StockSkill] Command: {cmd[:80]}")

        # ── 1. Portfolio operations ────────────────────────────────────────────
        if self._match(cmd, ["my portfolio", "show portfolio", "portfolio value",
                              "p&l", "profit loss", "profit and loss",
                              "holdings", "my stocks", "my shares"]):
            return self._handle_portfolio(cmd)

        if self._match(cmd, ["add shares", "buy shares", "i bought",
                               "i own", "add to portfolio", "shares of"]):
            return self._handle_add_holding(cmd)

        if self._match(cmd, ["remove from portfolio", "delete from portfolio",
                               "remove holding", "sell all"]):
            return self._handle_remove_holding(cmd)

        # ── 2. AI Analyst ──────────────────────────────────────────────────────
        if self._match(cmd, ["should i buy", "should i sell", "should i hold",
                               "analyze", "analyse", "why is", "why did",
                               "what do you think", "market outlook",
                               "good time to buy", "good investment",
                               "worth buying", "recommendation"]):
            return self._handle_analyst(cmd)

        # ── 3. Market News ─────────────────────────────────────────────────────
        if self._match(cmd, ["market news", "financial news", "stock news",
                               "business news", "latest news", "headlines"]):
            return self._handle_news(cmd)

        # ── 4. Watchlist ───────────────────────────────────────────────────────
        if self._match(cmd, ["add to watchlist", "watch", "watchlist",
                               "set alert", "alert when", "notify me",
                               "track stock", "price alert"]):
            return self._handle_watchlist(cmd)

        if self._match(cmd, ["show watchlist", "my watchlist",
                               "watchlist status", "watch list"]):
            return self._handle_show_watchlist(cmd)

        if self._match(cmd, ["remove from watchlist", "stop watching",
                               "delete from watchlist"]):
            return self._handle_remove_watchlist(cmd)

        # ── 5. Single stock quote (fallback) ───────────────────────────────────
        return self._handle_quote(cmd)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_portfolio(self, cmd: str) -> str:
        """Show full portfolio P&L panel."""
        import core.ui as ui
        from skills.stock_portfolio import get_portfolio_summary, portfolio_voice_summary

        summary = get_portfolio_summary()
        if summary["holdings"]:
            ui.stock_portfolio_panel(summary)
        return portfolio_voice_summary(summary)

    def _handle_add_holding(self, cmd: str) -> str:
        """Parse 'add 50 shares of RELIANCE at 2800' or '50 AAPL at 150'."""
        from skills.stock_api import extract_ticker
        from skills.stock_portfolio import add_holding

        ticker = extract_ticker(cmd)
        qty    = self._extract_number(cmd, pattern=r'(\d+(?:\.\d+)?)\s*(?:shares?|units?|qty)?')
        price  = self._extract_price(cmd)

        if not ticker:
            return (
                "I need a stock ticker to add to your portfolio. "
                "Try: add 50 shares of Reliance at 2800."
            )
        if not qty or qty <= 0:
            return f"How many shares of {ticker} did you buy?"
        if not price or price <= 0:
            return f"What was your buy price for {ticker}?"

        return add_holding(ticker, qty, price)

    def _handle_remove_holding(self, cmd: str) -> str:
        from skills.stock_api import extract_ticker
        from skills.stock_portfolio import remove_holding

        ticker = extract_ticker(cmd)
        if not ticker:
            return "Which stock do you want to remove from your portfolio?"
        return remove_holding(ticker)

    def _handle_analyst(self, cmd: str) -> str:
        """Route to AI market analyst."""
        import core.ui as ui
        from skills.stock_api import extract_ticker
        from skills.stock_analyst import analyze

        ticker = extract_ticker(cmd)
        ui.status(f"Consulting AI analyst{' for ' + ticker if ticker else ''}...", "wait")
        return analyze(cmd, ticker=ticker)

    def _handle_news(self, cmd: str) -> str:
        """Fetch and display market news."""
        import core.ui as ui
        from skills.stock_api import get_news, extract_ticker
        from skills.stock_analyst import tag_news_sentiment

        ticker = extract_ticker(cmd)
        ui.status("Fetching market news...", "wait")
        articles = get_news(ticker=ticker, count=5)

        # AI-tag sentiments (only if not already tagged by Alpha Vantage)
        for article in articles:
            if article.get("sentiment") == "Neutral" and article.get("headline"):
                # Only call AI for first 3 to preserve quota
                article["sentiment"] = tag_news_sentiment(article["headline"])

        ui.news_feed_panel(articles)

        # Spoken summary
        if articles and "unavailable" not in articles[0]["headline"].lower():
            count = len(articles)
            bulls = sum(1 for a in articles if a["sentiment"] == "Bullish")
            bears = sum(1 for a in articles if a["sentiment"] == "Bearish")
            return (
                f"Here are the latest {count} market headlines. "
                f"{bulls} bullish, {bears} bearish signals. "
                f"Top story: {articles[0]['headline'][:80]}."
            )
        return "Market news is currently unavailable. Check your Finnhub API key."

    def _handle_watchlist(self, cmd: str) -> str:
        """Add a stock to the watchlist, optionally with a price alert."""
        from skills.stock_api import extract_ticker
        from skills.stock_watchlist import add_to_watchlist

        ticker    = extract_ticker(cmd)
        alert_price = self._extract_price(cmd)
        direction = "above"
        if any(w in cmd for w in ["below", "drops", "falls", "under"]):
            direction = "below"
        elif any(w in cmd for w in ["above", "crosses", "hits", "reaches", "over"]):
            direction = "above"

        if not ticker:
            return (
                "Which stock do you want to watch? "
                "Try: add Apple to watchlist, or set alert when Tesla crosses 300."
            )
        return add_to_watchlist(ticker, alert_price=alert_price, direction=direction)

    def _handle_show_watchlist(self, cmd: str) -> str:
        import core.ui as ui
        from skills.stock_watchlist import get_watchlist_with_prices, watchlist_voice_summary

        items = get_watchlist_with_prices()
        if items:
            ui.watchlist_panel(items)
        return watchlist_voice_summary()

    def _handle_remove_watchlist(self, cmd: str) -> str:
        from skills.stock_api import extract_ticker
        from skills.stock_watchlist import remove_from_watchlist

        ticker = extract_ticker(cmd)
        if not ticker:
            return "Which stock do you want to remove from your watchlist?"
        return remove_from_watchlist(ticker)

    def _handle_quote(self, cmd: str) -> str:
        """Fetch and display a single stock quote."""
        import core.ui as ui
        from skills.stock_api import get_quote, extract_ticker

        ticker = extract_ticker(cmd)
        if not ticker:
            return (
                "I didn't catch a stock name. Try: price of Apple, "
                "or how is Reliance doing?"
            )

        ui.status(f"Fetching quote for {ticker}...", "wait")
        quote = get_quote(ticker)

        if quote.get("error") and not quote.get("price"):
            return f"I couldn't fetch data for {ticker}. {quote['error']}"

        ui.stock_quote_card(quote)

        # Spoken summary
        cached_note = " (cached data)" if quote.get("cached") else ""
        direction   = "up" if (quote.get("change", 0) or 0) >= 0 else "down"
        return (
            f"{quote.get('name', ticker)} is trading at "
            f"{quote['price']} {quote.get('currency','')}, "
            f"{direction} {abs(quote.get('change_pct', 0) or 0):.2f}% today{cached_note}."
        )

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _match(cmd: str, keywords: list) -> bool:
        """True if any keyword phrase appears in the command."""
        return any(k in cmd for k in keywords)

    @staticmethod
    def _extract_number(cmd: str, pattern: str) -> float | None:
        """Extract first number matching the given regex pattern."""
        match = re.search(pattern, cmd)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_price(cmd: str) -> float | None:
        """
        Extract a price from phrases like 'at 2800', 'at price 150.5',
        'crosses 300', 'above 4000', 'below 500'.
        """
        patterns = [
            r'at\s+(?:price\s+)?(\d+(?:\.\d+)?)',   # "at 2800" / "at price 150"
            r'(?:crosses|hits|reaches|above|below|over|under)\s+(\d+(?:\.\d+)?)',
            r'(?:rs\.?|₹|inr)\s*(\d+(?:\.\d+)?)',   # "Rs 2800" / "₹2800"
            r'\$\s*(\d+(?:\.\d+)?)',                  # "$150"
            r'(\d{3,}(?:\.\d+)?)',                    # bare number ≥ 3 digits (e.g. 2800)
        ]
        for p in patterns:
            match = re.search(p, cmd, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
