import React, { useEffect, useState, useRef } from "react";

interface StockEntry {
  ticker: string;
  company?: string;
  price: number;
  change: number;
  change_pct: number;
}

interface WatchlistData {
  holdings: StockEntry[];
  watching: StockEntry[];
  timestamp: string;
}

interface StockWatchlistProps {
  title?: string;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

function toNum(v: unknown): number {
  if (v == null) return 0;
  const n = typeof v === "string" ? parseFloat(v) : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 5) return "just now";
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function AIOSStockWatchlist({ title = "Stock Watchlist", onAction }: StockWatchlistProps) {
  const [data, setData] = useState<WatchlistData | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");
  const [agoText, setAgoText] = useState("connecting...");
  const esRef = useRef<EventSource | null>(null);

  // SSE subscription
  useEffect(() => {
    const es = new EventSource("/api/stocks/live");
    esRef.current = es;
    es.onmessage = (ev) => {
      try {
        const parsed: WatchlistData = JSON.parse(ev.data);
        setData(parsed);
        setLastRefreshed(parsed.timestamp);
      } catch { /* ignore parse errors */ }
    };
    es.onerror = () => {
      // EventSource auto-reconnects
    };
    return () => { es.close(); esRef.current = null; };
  }, []);

  // Update "ago" text every 10s
  useEffect(() => {
    if (!lastRefreshed) return;
    setAgoText(timeAgo(lastRefreshed));
    const iv = setInterval(() => setAgoText(timeAgo(lastRefreshed)), 10_000);
    return () => clearInterval(iv);
  }, [lastRefreshed]);

  const renderRow = (s: StockEntry) => {
    const p = toNum(s.price);
    const c = toNum(s.change_pct);
    const hasData = p > 0;
    const isPos = c >= 0;
    return (
      <div
        key={s.ticker}
        className="aios-stock-ticker"
        onClick={() => onAction?.("stock_clicked", { ticker: s.ticker })}
      >
        <span className="ticker-symbol">{s.ticker}</span>
        <span className="ticker-company">{s.company || s.ticker}</span>
        <span className="ticker-price">{hasData ? `$${p.toFixed(2)}` : "—"}</span>
        <span className={`ticker-change ${hasData ? (isPos ? "positive" : "negative") : ""}`}>
          {hasData ? `${isPos ? "+" : ""}${c.toFixed(2)}%` : ""}
        </span>
      </div>
    );
  };

  if (!data) {
    return (
      <div className="aios-stock-watchlist">
        <div className="aios-text--muted" style={{ padding: "16px", textAlign: "center" }}>
          Connecting to live stock feed...
        </div>
      </div>
    );
  }

  return (
    <div className="aios-stock-watchlist">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <span className="aios-text--title" style={{ fontWeight: 600 }}>{title}</span>
        <span className="aios-text--muted" style={{ fontSize: "11px" }}>
          🔄 {agoText}
        </span>
      </div>
      {data.holdings.length > 0 && (
        <>
          <div className="aios-text--muted" style={{ fontSize: "11px", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Holdings
          </div>
          {data.holdings.map(renderRow)}
        </>
      )}
      {data.watching.length > 0 && (
        <>
          <div className="aios-text--muted" style={{ fontSize: "11px", margin: "10px 0 6px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Watching
          </div>
          {data.watching.map(renderRow)}
        </>
      )}
    </div>
  );
}
