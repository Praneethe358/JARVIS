"""
skills/stock_portfolio.py
──────────────────────────
Portfolio management for the NEXUS Stock Market Intelligence Module.

Stores holdings in data/portfolio.json:
  { "holdings": [ { "ticker", "qty", "buy_price", "added" }, ... ] }

Computes live P&L by fetching current prices via stock_api.
"""

import json
import os
from datetime import datetime
from core.logger import log

_PORTFOLIO_PATH = os.path.join("data", "portfolio.json")


# ── Persistence ────────────────────────────────────────────────────────────────

def _load() -> dict:
    """Load portfolio from JSON file. Creates default if missing."""
    if not os.path.exists(_PORTFOLIO_PATH):
        _save({"holdings": []})
    with open(_PORTFOLIO_PATH, "r") as f:
        return json.load(f)


def _save(data: dict):
    """Persist portfolio to JSON file."""
    os.makedirs("data", exist_ok=True)
    with open(_PORTFOLIO_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def add_holding(ticker: str, qty: float, buy_price: float) -> str:
    """
    Add or update a holding in the portfolio.
    If the ticker already exists, averages in the new purchase.
    Returns a confirmation string for TTS.
    """
    ticker = ticker.upper().strip()
    data = _load()

    # Check if ticker already in portfolio — average down/up
    for h in data["holdings"]:
        if h["ticker"] == ticker:
            total_qty = h["qty"] + qty
            avg_price = ((h["qty"] * h["buy_price"]) + (qty * buy_price)) / total_qty
            h["qty"]       = total_qty
            h["buy_price"] = round(avg_price, 2)
            _save(data)
            log.info(f"[Portfolio] Updated {ticker}: qty={total_qty}, avg={avg_price:.2f}")
            return (
                f"Updated {ticker}. Total quantity: {total_qty:.0f} shares "
                f"at average price {avg_price:.2f}."
            )

    # New holding
    data["holdings"].append({
        "ticker"   : ticker,
        "qty"      : qty,
        "buy_price": round(buy_price, 2),
        "added"    : datetime.now().strftime("%Y-%m-%d"),
    })
    _save(data)
    log.info(f"[Portfolio] Added {ticker}: qty={qty}, buy={buy_price}")
    return (
        f"Added {ticker} to your portfolio. "
        f"{qty:.0f} shares at {buy_price:.2f} per share."
    )


def remove_holding(ticker: str) -> str:
    """Remove a holding from the portfolio."""
    ticker = ticker.upper().strip()
    data = _load()
    before = len(data["holdings"])
    data["holdings"] = [h for h in data["holdings"] if h["ticker"] != ticker]
    if len(data["holdings"]) < before:
        _save(data)
        return f"Removed {ticker} from your portfolio."
    return f"{ticker} was not found in your portfolio."


def get_portfolio_summary() -> dict:
    """
    Compute live portfolio summary. Returns:
      {
        "holdings": [ { ticker, name, qty, buy_price, current_price,
                         change_pct, pnl, pnl_pct, value, currency,
                         cached, error } ],
        "total_invested": float,
        "total_current" : float,
        "total_pnl"     : float,
        "total_pnl_pct" : float,
      }
    """
    from skills.stock_api import get_quote

    data = _load()
    holdings = data.get("holdings", [])

    if not holdings:
        return {
            "holdings": [], "total_invested": 0,
            "total_current": 0, "total_pnl": 0, "total_pnl_pct": 0,
        }

    enriched = []
    total_invested = 0.0
    total_current  = 0.0

    for h in holdings:
        quote = get_quote(h["ticker"])
        current_price = quote.get("price")
        invested_val  = h["qty"] * h["buy_price"]
        total_invested += invested_val

        if current_price is not None:
            current_val = h["qty"] * current_price
            pnl         = current_val - invested_val
            pnl_pct     = (pnl / invested_val * 100) if invested_val else 0
            total_current += current_val
        else:
            current_val = None
            pnl         = None
            pnl_pct     = None

        enriched.append({
            "ticker"       : h["ticker"],
            "name"         : quote.get("name", h["ticker"]),
            "qty"          : h["qty"],
            "buy_price"    : h["buy_price"],
            "current_price": round(current_price, 2) if current_price else None,
            "change_pct"   : quote.get("change_pct"),
            "pnl"          : round(pnl, 2) if pnl is not None else None,
            "pnl_pct"      : round(pnl_pct, 2) if pnl_pct is not None else None,
            "value"        : round(current_val, 2) if current_val else None,
            "currency"     : quote.get("currency", "USD"),
            "cached"       : quote.get("cached", False),
            "error"        : quote.get("error"),
        })

    total_pnl     = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

    return {
        "holdings"     : enriched,
        "total_invested": round(total_invested, 2),
        "total_current" : round(total_current, 2),
        "total_pnl"    : round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
    }


def portfolio_voice_summary(summary: dict) -> str:
    """
    Generate a TTS-friendly summary of the portfolio.
    """
    if not summary["holdings"]:
        return "Your portfolio is empty. Add stocks by saying: add 50 shares of Reliance at 2800."

    total_pnl = summary["total_pnl"]
    total_pnl_pct = summary["total_pnl_pct"]
    direction = "up" if total_pnl >= 0 else "down"

    parts = [
        f"Your portfolio is {direction} {abs(total_pnl_pct):.1f}% overall, "
        f"with a {'profit' if total_pnl >= 0 else 'loss'} of "
        f"{abs(total_pnl):.0f}. "
        f"Total value: {summary['total_current']:.0f}. "
    ]

    # Top winner and loser
    valid = [h for h in summary["holdings"] if h["pnl"] is not None]
    if valid:
        top    = max(valid, key=lambda h: h["pnl_pct"])
        bottom = min(valid, key=lambda h: h["pnl_pct"])
        if top["pnl_pct"] > 0:
            parts.append(
                f"Best performer: {top['ticker']} at {top['pnl_pct']:.1f}% gain. "
            )
        if bottom["pnl_pct"] < 0:
            parts.append(
                f"Worst performer: {bottom['ticker']} at {abs(bottom['pnl_pct']):.1f}% loss. "
            )

    return "".join(parts)
