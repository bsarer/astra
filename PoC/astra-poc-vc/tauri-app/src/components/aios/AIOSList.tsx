import React from "react";

interface AIOSListProps {
  ordered?: boolean;
  children?: React.ReactNode;
}

export function AIOSList({ ordered = false, children }: AIOSListProps) {
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag style={{ paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "4px" }}>
      {React.Children.map(children, (child) => (
        <li style={{ fontSize: "14px" }}>{child}</li>
      ))}
    </Tag>
  );
}
