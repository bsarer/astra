import React from "react";

interface SparklineChartProps {
  values?: number[];
  color?: "green" | "red" | "blue" | "cyan";
  height?: string;
}

const colorMap: Record<string, string> = {
  green: "var(--accent-green)",
  red: "var(--accent-red)",
  blue: "var(--accent-blue)",
  cyan: "var(--accent-cyan)",
};

export function AIOSSparklineChart({ values = [], color = "cyan", height = "40px" }: SparklineChartProps) {
  const max = Math.max(...values, 1);
  const barColor = colorMap[color] || colorMap.cyan;

  return (
    <div className="aios-sparkline" style={{ height }}>
      {values.map((v, i) => (
        <div
          key={i}
          className="aios-sparkline-bar"
          style={{ height: `${(v / max) * 100}%`, background: barColor }}
        />
      ))}
    </div>
  );
}
