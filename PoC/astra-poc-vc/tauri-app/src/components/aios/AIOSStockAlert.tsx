import React from "react";

interface StockAlertProps {
  title?: string;
  source?: string;
  sentiment?: "bullish" | "bearish" | "neutral";
  tickers?: Array<{ ticker: string; price: number; change_pct: number }>;
  actions?: Array<{ label: string; action: string; payload?: Record<string, any> }>;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

export function AIOSStockAlert({
  title = "",
  source = "",
  sentiment = "neutral",
  tickers = [],
  actions = [],
  onAction,
}: StockAlertProps) {
  const icon = sentiment === "bullish" ? "📈" : sentiment === "bearish" ? "📉" : "📊";
  return (
    <div className={`aios-stock-alert aios-stock-alert--${sentiment}`}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
        <span style={{ fontSize: "18px" }}>{icon}</span>
        <span className="aios-text--title" style={{ fontSize: "15px" }}>{title}</span>
      </div>
      {source && <div className="aios-text--muted" style={{ marginBottom: "10px" }}>Source: {source}</div>}
      {tickers.length > 0 && (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "10px" }}>
          {tickers.map((t) => (
            <span key={t.ticker} style={{ fontSize: "13px", fontWeight: 600 }}>
              {t.ticker} ${t.price?.toFixed(2)}{" "}
              <span style={{ color: t.change_pct >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                {t.change_pct >= 0 ? "+" : ""}{t.change_pct?.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      )}
      {actions.length > 0 && (
        <div style={{ display: "flex", gap: "6px" }}>
          {actions.map((a, i) => (
            <button key={i} className="aios-btn aios-btn--ghost" onClick={() => onAction?.(a.action, a.payload)}>
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
