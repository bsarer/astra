import React from "react";

interface AIOSFallbackProps {
  type?: string;
  props?: Record<string, any>;
  children?: React.ReactNode;
}

export function AIOSFallback({ type = "Unknown", props = {}, children }: AIOSFallbackProps) {
  return (
    <div className="aios-card aios-card--outlined">
      <span className="aios-text--muted">Unknown component: {type}</span>
      <pre className="aios-fallback-json">{JSON.stringify(props, null, 2)}</pre>
      {children}
    </div>
  );
}
