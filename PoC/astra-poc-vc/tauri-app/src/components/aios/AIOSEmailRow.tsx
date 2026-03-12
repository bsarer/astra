import React from "react";

interface EmailRowProps {
  email_id?: string;
  from_name?: string;
  initial?: string;
  subject?: string;
  preview?: string;
  time?: string;
  actions?: Array<{ label: string; action: string }>;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

export function AIOSEmailRow({
  email_id = "",
  from_name = "",
  initial = "",
  subject = "",
  preview = "",
  time = "",
  onAction,
}: EmailRowProps) {
  return (
    <div className="aios-email-row" onClick={() => onAction?.("email_clicked", { email_id })}>
      <div className="email-avatar">{initial || from_name.charAt(0)}</div>
      <div className="email-content">
        <div className="email-subject">{subject}</div>
        <div className="email-preview">{from_name} — {preview}</div>
      </div>
      <div className="email-time">{time}</div>
    </div>
  );
}
