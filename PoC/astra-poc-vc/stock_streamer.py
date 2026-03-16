"""Background stock data streamer — pushes live watchlist data via SSE.

Fetches fresh stock prices every STOCK_REFRESH_INTERVAL seconds and
broadcasts to all connected SSE clients. No LLM involvement.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("astra.stocks")

STOCK_REFRESH_INTERVAL = int(os.getenv("STOCK_REFRESH_INTERVAL", "60"))

# Latest snapshot — shared across SSE clients
_latest_snapshot: dict | None = None
_subscribers: set[asyncio.Queue] = set()


def _fetch_watchlist() -> dict:
    """Synchronous yfinance fetch — run in executor."""
    import yfinance as yf
    from tools_stock import MIKE_WATCHLIST, ALL_TICKERS, _safe

    result = {"holdings": [], "watching": [], "timestamp": datetime.now().isoformat()}

    for category, tickers in [("holdings", MIKE_WATCHLIST["holdings"]),
                               ("watching", MIKE_WATCHLIST["watching"])]:
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d")
                if hist.empty:
                    result[category].append({"ticker": ticker, "price": 0, "change": 0, "change_pct": 0})
                    continue
                current = _safe(hist["Close"].iloc[-1])
                prev = _safe(hist["Close"].iloc[-2] if len(hist) > 1 else current) or 1
                change = current - prev
                change_pct = (change / prev) * 100 if prev else 0
                info = stock.info
                result[category].append({
                    "ticker": ticker,
                    "company": info.get("shortName", ticker),
                    "price": round(_safe(current), 2),
                    "change": round(_safe(change), 2),
                    "change_pct": round(_safe(change_pct), 2),
                })
            except Exception:
                result[category].append({"ticker": ticker, "price": 0, "change": 0, "change_pct": 0})

    return result


async def _refresh_loop():
    """Background loop: fetch stock data and broadcast to subscribers."""
    global _latest_snapshot
    loop = asyncio.get_event_loop()

    logger.info("Stock streamer started (interval=%ds)", STOCK_REFRESH_INTERVAL)

    while True:
        try:
            snapshot = await loop.run_in_executor(None, _fetch_watchlist)
            _latest_snapshot = snapshot
            data = json.dumps(snapshot)
            dead: list[asyncio.Queue] = []
            for q in _subscribers:
                try:
                    q.put_nowait(data)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                _subscribers.discard(q)
            logger.debug("Stock refresh broadcast to %d clients", len(_subscribers))
        except Exception as e:
            logger.warning("Stock refresh error: %s", e)

        await asyncio.sleep(STOCK_REFRESH_INTERVAL)


_refresh_task: asyncio.Task | None = None


def ensure_started():
    """Start the background refresh loop if not already running."""
    global _refresh_task
    if _refresh_task is None or _refresh_task.done():
        _refresh_task = asyncio.create_task(_refresh_loop())


async def subscribe():
    """Async generator yielding SSE-formatted stock updates."""
    q: asyncio.Queue = asyncio.Queue(maxsize=5)
    _subscribers.add(q)

    # Send latest snapshot immediately if available
    if _latest_snapshot:
        yield f"data: {json.dumps(_latest_snapshot)}\n\n"

    try:
        while True:
            data = await q.get()
            yield f"data: {data}\n\n"
    finally:
        _subscribers.discard(q)
