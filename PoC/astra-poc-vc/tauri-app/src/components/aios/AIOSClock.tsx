import React, { useState, useEffect } from "react";

interface ClockProps {
  timezone?: string;   // e.g. "America/New_York", defaults to local
  format?: "12h" | "24h";
  showDate?: boolean;
  label?: string;
}

export function AIOSClock({ timezone, format = "12h", showDate = true, label }: ClockProps) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const opts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: format === "12h",
    ...(timezone ? { timeZone: timezone } : {}),
  };

  const dateOpts: Intl.DateTimeFormatOptions = {
    weekday: "short",
    month: "short",
    day: "numeric",
    ...(timezone ? { timeZone: timezone } : {}),
  };

  const timeStr = now.toLocaleTimeString(undefined, opts);
  const dateStr = now.toLocaleDateString(undefined, dateOpts);

  return (
    <div className="aios-clock">
      {label && <div className="clock-label">{label}</div>}
      <div className="clock-time">{timeStr}</div>
      {showDate && <div className="clock-date">{dateStr}</div>}
      {timezone && <div className="clock-tz">{timezone.replace(/_/g, " ")}</div>}
    </div>
  );
}
