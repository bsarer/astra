import React from "react";

interface AIOSIconProps {
  name?: string;
  size?: string;
  color?: string;
}

export function AIOSIcon({ name = "●", size = "16px", color }: AIOSIconProps) {
  return <span style={{ fontSize: size, color, lineHeight: 1 }}>{name}</span>;
}
