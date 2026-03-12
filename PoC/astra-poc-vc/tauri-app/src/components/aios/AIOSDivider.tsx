import React from "react";

interface AIOSDividerProps {
  spacing?: string;
}

export function AIOSDivider({ spacing = "12px" }: AIOSDividerProps) {
  return <hr className="aios-divider" style={{ margin: `${spacing} 0` }} />;
}
