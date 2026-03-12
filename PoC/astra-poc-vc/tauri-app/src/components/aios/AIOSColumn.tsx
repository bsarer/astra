import React from "react";

interface AIOSColumnProps {
  children?: React.ReactNode;
  gap?: string;
  align?: "start" | "center" | "end" | "stretch";
}

export function AIOSColumn({ children, gap = "8px", align = "start" }: AIOSColumnProps) {
  return (
    <div
      className="aios-column"
      style={{ gap, alignItems: align === "stretch" ? "stretch" : `flex-${align}` }}
    >
      {children}
    </div>
  );
}
