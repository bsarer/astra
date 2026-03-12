import React from "react";

interface AIOSButtonProps {
  label?: string;
  action?: string;
  payload?: Record<string, any>;
  variant?: "primary" | "secondary" | "ghost";
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

export function AIOSButton({ label = "Button", action = "", payload, variant = "primary", onAction }: AIOSButtonProps) {
  return (
    <button
      className={`aios-btn aios-btn--${variant}`}
      onClick={() => onAction?.(action, payload)}
    >
      {label}
    </button>
  );
}
