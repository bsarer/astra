import React from "react";

interface AIOSTextProps {
  text?: string;
  variant?: "title" | "body" | "secondary" | "muted";
  weight?: "bold" | "semibold" | "normal";
}

export function AIOSText({ text = "", variant = "body", weight = "normal" }: AIOSTextProps) {
  return (
    <span className={`aios-text--${variant}`} style={{ fontWeight: weight }}>
      {text}
    </span>
  );
}
