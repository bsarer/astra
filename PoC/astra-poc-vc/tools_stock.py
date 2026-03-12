"""Stock market tools — real data via yfinance + portfolio context."""

import json
from datetime import datetime, timedelta
from typing import List, Optional
from langchain_core.tools import tool

# Mike's watchlist for context-aware filtering
MIKE_WATCHLIST = {
    "holdings": ["AAPL", "MSFT", "NVDA", "TSLA"],
    "watching": ["GOOG", "AMZN", "META"],
}

ALL_TICKERS = MIKE_WATCHLIST["holdings"] + MIKE_WATCHLIST["watching"]


@tool
def get_stock_quote(ticker: str) -> str:
    """Get real-time stock quote for a ticker symbol (e.g. AAPL, MSFT, NVDA).
    Returns current price, change, volume, and key metrics."""
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="2d")

        if hist.empty:
            return json.dumps({"error": f"No data found for {ticker}"})

        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = current - prev
        change_pct = (change / prev) * 100 if prev else 0

        return json.dumps({
            "ticker": ticker.upper(),
            "price": round(current, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(hist["Volume"].iloc[-1]),
            "day_high": round(hist["High"].iloc[-1], 2),
            "day_low": round(hist["Low"].iloc[-1], 2),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "name": info.get("shortName", ticker.upper()),
            "in_watchlist": ticker.upper() in ALL_TICKERS,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch {ticker}: {str(e)}"})


@tool
def get_watchlist_summary() -> str:
    """Get a summary of all stocks in Mike's watchlist (holdings + watching).
    Returns prices, daily changes, and portfolio overview."""
    import yfinance as yf

    results = {"holdings": [], "watching": [], "timestamp": datetime.now().isoformat()}

    for category, tickers in [("holdings", MIKE_WATCHLIST["holdings"]),
                               ("watching", MIKE_WATCHLIST["watching"])]:
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d")
                if hist.empty:
                    continue
                current = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
                change = current - prev
                change_pct = (change / prev) * 100 if prev else 0
                results[category].append({
                    "ticker": ticker,
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "signal": "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪",
                })
            except:
                results[category].append({"ticker": ticker, "error": "fetch failed"})

    return json.dumps(results, indent=2)


@tool
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """Get historical price data for a stock. Period can be: 1d, 5d, 1mo, 3mo, 6mo, 1y.
    Returns daily OHLCV data for charting."""
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)
        if hist.empty:
            return json.dumps({"error": f"No history for {ticker}"})

        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        return json.dumps({
            "ticker": ticker.upper(),
            "period": period,
            "data_points": len(data),
            "history": data,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch history for {ticker}: {str(e)}"})


@tool
def analyze_stock_email_context(email_subject: str, email_body: str, email_id: str = "") -> str:
    """Analyze an email for stock market signals relevant to Mike's watchlist.
    Extracts mentioned tickers, sentiment, and fetches real-time data for matches.
    Use this when an email mentions stocks, market movements, or financial news.
    Pass email_id to avoid re-processing the same email."""
    # Import canvas tracking from agent module
    from agent import _processed_email_ids

    # Skip if already processed
    if email_id and email_id in _processed_email_ids:
        return json.dumps({"relevant": False, "already_processed": True,
                           "message": f"Email {email_id} was already analyzed — skipping."})

    import yfinance as yf
    import re

    # Known ticker patterns and company name mappings
    company_to_ticker = {
        "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "tesla": "TSLA",
        "google": "GOOG", "alphabet": "GOOG", "amazon": "AMZN", "meta": "META",
        "facebook": "META",
    }

    text = (email_subject + " " + email_body).lower()

    # Find mentioned tickers
    found_tickers = set()

    # Match $TICKER or standalone ticker symbols
    ticker_pattern = re.findall(r'\$([A-Z]{2,5})', email_subject + " " + email_body)
    for t in ticker_pattern:
        if t in ALL_TICKERS:
            found_tickers.add(t)

    # Match company names
    for name, ticker in company_to_ticker.items():
        if name in text:
            found_tickers.add(ticker)

    if not found_tickers:
        return json.dumps({"relevant": False, "message": "No watchlist stocks mentioned in this email."})

    # Detect sentiment keywords
    bullish_words = ["upswing", "surge", "rally", "bullish", "upgrade", "buy", "outperform",
                     "beat", "exceeded", "growth", "record high", "breakout", "momentum",
                     "strong", "positive", "upside", "target raised", "price target"]
    bearish_words = ["downgrade", "sell", "bearish", "decline", "miss", "warning",
                     "underperform", "risk", "drop", "crash", "correction", "weak"]

    bull_count = sum(1 for w in bullish_words if w in text)
    bear_count = sum(1 for w in bearish_words if w in text)
    sentiment = "bullish" if bull_count > bear_count else "bearish" if bear_count > bull_count else "neutral"

    # Fetch real-time data for matched tickers
    stock_data = []
    for ticker in found_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist.empty:
                continue
            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
            change_pct = ((current - prev) / prev) * 100 if prev else 0
            week_start = hist["Close"].iloc[0]
            week_change = ((current - week_start) / week_start) * 100

            stock_data.append({
                "ticker": ticker,
                "price": round(current, 2),
                "daily_change_pct": round(change_pct, 2),
                "weekly_change_pct": round(week_change, 2),
                "in_holdings": ticker in MIKE_WATCHLIST["holdings"],
            })
        except:
            pass

    # Mark email as processed
    if email_id:
        _processed_email_ids.add(email_id)

    return json.dumps({
        "relevant": True,
        "sentiment": sentiment,
        "bull_signals": bull_count,
        "bear_signals": bear_count,
        "matched_tickers": list(found_tickers),
        "stock_data": stock_data,
        "email_id": email_id,
        "action": f"Stock alert: {sentiment} signal detected for {', '.join(found_tickers)} from email",
    }, indent=2)


# All stock tools for easy import
stock_tools = [
    get_stock_quote,
    get_watchlist_summary,
    get_stock_history,
    analyze_stock_email_context,
]
