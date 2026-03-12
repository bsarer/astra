import React, { useState } from "react";

interface AIOSTabsProps {
  labels?: string[];
  active?: number;
  children?: React.ReactNode;
  onTabChange?: (index: number) => void;
}

export function AIOSTabs({ labels = [], active = 0, children, onTabChange }: AIOSTabsProps) {
  const [activeTab, setActiveTab] = useState(active);
  const childArray = React.Children.toArray(children);

  const handleTabClick = (index: number) => {
    setActiveTab(index);
    onTabChange?.(index);
  };

  return (
    <div>
      <div className="aios-tabs-bar">
        {labels.map((label, i) => (
          <button
            key={i}
            className={`aios-tab ${i === activeTab ? "aios-tab--active" : ""}`}
            onClick={() => handleTabClick(i)}
          >
            {label}
          </button>
        ))}
      </div>
      <div>{childArray[activeTab] ?? null}</div>
    </div>
  );
}
