import React from "react";

interface StockTickerProps {
  ticker?: string;
  company?: string;
  price?: number | string;
  change_pct?: number | string;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

function toNum(v: unknown): number | null {
  if (v == null) return null;
  const n = typeof v === "string" ? parseFloat(v) : Number(v);
  return Number.isFinite(n) ? n : null;
}

export function AIOSStockTicker({ ticker = "", company = "", price, change_pct, onAction }: StockTickerProps) {
  const p = toNum(price);
  const c = toNum(change_pct);
  const hasData = p !== null && p > 0;
  const isPositive = (c ?? 0) >= 0;
  return (
    <div className="aios-stock-ticker" onClick={() => onAction?.("stock_clicked", { ticker })}>
      <span className="ticker-symbol">{ticker}</span>
      <span className="ticker-company">{company}</span>
      <span className="ticker-price">{hasData ? `$${p.toFixed(2)}` : "—"}</span>
      <span className={`ticker-change ${hasData ? (isPositive ? "positive" : "negative") : ""}`}>
        {hasData && c !== null ? `${isPositive ? "+" : ""}${c.toFixed(2)}%` : ""}
      </span>
    </div>
  );
}
