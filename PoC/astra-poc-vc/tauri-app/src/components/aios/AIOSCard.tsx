import React from "react";

interface AIOSCardProps {
  children?: React.ReactNode;
  padding?: string;
  variant?: "glass" | "flat" | "outlined";
}

export function AIOSCard({ children, padding = "16px", variant = "glass" }: AIOSCardProps) {
  return (
    <div className={`aios-card aios-card--${variant}`} style={{ padding }}>
      {children}
    </div>
  );
}
