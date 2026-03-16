import React from "react";

interface StockTickerProps {
  ticker?: string;
  company?: string;
  price?: number;
  change_pct?: number;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

export function AIOSStockTicker({ ticker = "", company = "", price, change_pct, onAction }: StockTickerProps) {
  const p = price ?? 0;
  const c = change_pct ?? 0;
  const isPositive = c >= 0;
  return (
    <div className="aios-stock-ticker" onClick={() => onAction?.("stock_clicked", { ticker })}>
      <span className="ticker-symbol">{ticker}</span>
      <span className="ticker-company">{company}</span>
      <span className="ticker-price">${p.toFixed(2)}</span>
      <span className={`ticker-change ${isPositive ? "positive" : "negative"}`}>
        {isPositive ? "+" : ""}{c.toFixed(2)}%
      </span>
    </div>
  );
}
