import React from "react";

interface MetricCardProps {
  label?: string;
  value?: string;
  change?: string;
  color?: string;
  action?: string;
  payload?: Record<string, any>;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

export function AIOSMetricCard({ label = "", value = "", change = "", color, action, payload, onAction }: MetricCardProps) {
  return (
    <div className="aios-metric-card" onClick={() => action && onAction?.(action, payload)}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>{value}</div>
      {change && <div className="metric-change" style={{ color }}>{change}</div>}
    </div>
  );
}
