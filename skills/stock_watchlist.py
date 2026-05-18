"""
skills/stock_watchlist.py
──────────────────────────
Watchlist management + background price alert polling.

Stores watchlist in data/watchlist.json:
  {
    "items": [
      { "ticker", "alert_price", "direction", "added", "triggered" }
    ]
  }

  direction: "above" | "below"  — alert fires when price crosses threshold.

Background thread polls prices every 60s (configurable via config.json:
  watchlist_poll_interval_seconds) and fires ui.reminder_box() + desktop
  notify-send when a threshold is breached.
"""

import json
import os
import time
import threading
import subprocess
from datetime import datetime
from core.logger import log

_WATCHLIST_PATH = os.path.join("data", "watchlist.json")

# Reference to the running poll thread (singleton)
_poll_thread: threading.Thread | None = None
_stop_event   = threading.Event()


# ── Persistence ────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(_WATCHLIST_PATH):
        _save({"items": []})
    with open(_WATCHLIST_PATH, "r") as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(_WATCHLIST_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def add_to_watchlist(ticker: str, alert_price: float = None, direction: str = "above") -> str:
    """
    Add a ticker to the watchlist with optional price alert.
    Returns TTS confirmation string.
    """
    ticker = ticker.upper().strip()
    data = _load()

    # Remove existing entry for same ticker to avoid duplicates
    data["items"] = [i for i in data["items"] if i["ticker"] != ticker]

    item = {
        "ticker"     : ticker,
        "alert_price": alert_price,
        "direction"  : direction.lower(),
        "added"      : datetime.now().strftime("%Y-%m-%d %H:%M"),
        "triggered"  : False,
    }
    data["items"].append(item)
    _save(data)
    log.info(f"[Watchlist] Added {ticker}, alert={alert_price}, dir={direction}")

    if alert_price:
        return (
            f"Added {ticker} to your watchlist. "
            f"I'll alert you when price goes {direction} {alert_price:.2f}."
        )
    return f"Added {ticker} to your watchlist. I'll track it for you."


def remove_from_watchlist(ticker: str) -> str:
    """Remove a ticker from the watchlist."""
    ticker = ticker.upper().strip()
    data = _load()
    before = len(data["items"])
    data["items"] = [i for i in data["items"] if i["ticker"] != ticker]
    if len(data["items"]) < before:
        _save(data)
        return f"Removed {ticker} from your watchlist."
    return f"{ticker} was not found in your watchlist."


def get_watchlist_with_prices() -> list[dict]:
    """
    Return watchlist items enriched with current prices and alert status.
    Each item: { ticker, name, price, change_pct, alert_price, direction, status }
    """
    from skills.stock_api import get_quote
    data = _load()
    enriched = []
    for item in data["items"]:
        quote  = get_quote(item["ticker"])
        price  = quote.get("price")
        status = "No alert set"
        if item.get("alert_price") and price:
            if item["direction"] == "above" and price >= item["alert_price"]:
                status = f"⚡ TRIGGERED — above {item['alert_price']:.2f}"
            elif item["direction"] == "below" and price <= item["alert_price"]:
                status = f"⚡ TRIGGERED — below {item['alert_price']:.2f}"
            else:
                status = f"Watching for {item['direction']} {item['alert_price']:.2f}"
        enriched.append({
            "ticker"     : item["ticker"],
            "name"       : quote.get("name", item["ticker"]),
            "price"      : price,
            "change_pct" : quote.get("change_pct"),
            "alert_price": item.get("alert_price"),
            "direction"  : item.get("direction", "above"),
            "triggered"  : item.get("triggered", False),
            "status"     : status,
            "cached"     : quote.get("cached", False),
        })
    return enriched


def watchlist_voice_summary() -> str:
    """TTS-friendly watchlist summary."""
    data = _load()
    items = data.get("items", [])
    if not items:
        return "Your watchlist is empty. Add a stock by saying: add Reliance to watchlist."

    count = len(items)
    tickers = ", ".join(i["ticker"] for i in items[:5])
    suffix = f" and {count - 5} more" if count > 5 else ""
    return f"You're watching {count} stocks: {tickers}{suffix}."


# ── Background polling ─────────────────────────────────────────────────────────

def start_watchlist_polling():
    """
    Start the background thread that polls watchlist prices every N seconds.
    Safe to call multiple times — only one thread runs at a time.
    """
    global _poll_thread, _stop_event

    if _poll_thread and _poll_thread.is_alive():
        log.info("[Watchlist] Polling thread already running.")
        return

    _stop_event.clear()
    _poll_thread = threading.Thread(target=_poll_loop, daemon=True, name="watchlist-poll")
    _poll_thread.start()
    log.info("[Watchlist] Background polling thread started.")


def stop_watchlist_polling():
    """Signal the background polling thread to stop."""
    _stop_event.set()
    log.info("[Watchlist] Polling thread stop requested.")


def _poll_loop():
    """Background loop — checks prices and fires alerts on threshold breaches."""
    from core.config import CONFIG
    import core.ui as ui
    from skills.stock_api import get_quote

    interval = CONFIG.get("watchlist_poll_interval_seconds", 60)
    log.info(f"[Watchlist] Polling every {interval}s")

    while not _stop_event.is_set():
        try:
            _check_alerts(ui, get_quote)
        except Exception as e:
            log.warning(f"[Watchlist] Poll error: {e}")
        # Sleep in 1s chunks so we can respond to stop_event quickly
        for _ in range(int(interval)):
            if _stop_event.is_set():
                break
            time.sleep(1)

    log.info("[Watchlist] Polling thread exited.")


def _check_alerts(ui, get_quote):
    """Check each watchlist item and fire alerts if thresholds are breached."""
    data = _load()
    changed = False

    for item in data["items"]:
        if not item.get("alert_price"):
            continue
        if item.get("triggered"):
            continue   # already fired — don't spam

        quote = get_quote(item["ticker"])
        price = quote.get("price")
        if price is None:
            continue

        fired = False
        msg   = ""
        if item["direction"] == "above" and price >= item["alert_price"]:
            fired = True
            msg = (
                f"⚡ ALERT: {item['ticker']} crossed ABOVE {item['alert_price']:.2f} "
                f"— currently at {price:.2f}"
            )
        elif item["direction"] == "below" and price <= item["alert_price"]:
            fired = True
            msg = (
                f"⚡ ALERT: {item['ticker']} dropped BELOW {item['alert_price']:.2f} "
                f"— currently at {price:.2f}"
            )

        if fired:
            item["triggered"] = True
            changed = True
            log.info(f"[Watchlist] Alert fired: {msg}")
            # ── Terminal alert ───────────────────────────────────────────────
            ui.reminder_box(msg)
            # ── Desktop notification (best-effort) ───────────────────────────
            try:
                subprocess.Popen(
                    ["notify-send", "--urgency=critical",
                     f"NEXUS Stock Alert: {item['ticker']}", msg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass   # notify-send not available — terminal alert is enough

    if changed:
        _save(data)
