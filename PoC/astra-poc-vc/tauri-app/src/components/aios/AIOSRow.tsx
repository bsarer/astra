import React from "react";

interface AIOSRowProps {
  children?: React.ReactNode;
  gap?: string;
  align?: "start" | "center" | "end" | "stretch";
  wrap?: boolean;
}

export function AIOSRow({ children, gap = "8px", align = "start", wrap = false }: AIOSRowProps) {
  return (
    <div
      className="aios-row"
      style={{ gap, alignItems: align === "stretch" ? "stretch" : `flex-${align}`, flexWrap: wrap ? "wrap" : "nowrap" }}
    >
      {children}
    </div>
  );
}
