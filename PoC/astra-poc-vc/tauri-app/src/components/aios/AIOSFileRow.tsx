import React from "react";

interface FileRowProps {
  filename?: string;
  size?: string;
  type?: string;
  path?: string;
  modified?: string;
  domains?: string[];
  preview?: string;
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

function getTypeAccent(type: string): string {
  const t = (type || "").toLowerCase();
  if (t === "pdf") return "#ef4444";
  if (["image", "png", "jpg", "jpeg", "webp", "gif", "svg"].includes(t)) return "#a855f7";
  if (["video", "mp4", "mov", "avi", "mkv"].includes(t)) return "#3b82f6";
  if (["doc", "docx", "txt", "md", "rtf", "document"].includes(t)) return "#06b6d4";
  if (["xls", "xlsx", "csv", "spreadsheet"].includes(t)) return "#22c55e";
  return "#64748b";
}

function getTypeLabel(type: string): string {
  const t = (type || "").toLowerCase();
  if (t === "document") return "DOC";
  if (t === "spreadsheet") return "XLS";
  return t.toUpperCase().slice(0, 4);
}

export function AIOSFileRow({
  filename = "",
  size = "",
  type = "",
  path = "",
  modified = "",
  domains = [],
  preview = "",
  onAction,
}: FileRowProps) {
  const accent = getTypeAccent(type);
  const label = getTypeLabel(type);

  return (
    <div
      className="aios-file-row"
      role="button"
      tabIndex={0}
      onClick={() => onAction?.("open_file", { path: path || filename, filename })}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onAction?.("open_file", { path: path || filename, filename });
        }
      }}
    >
      <span
        className="aios-file-row__badge"
        style={{
          color: accent,
          borderColor: `${accent}55`,
          background: `${accent}18`,
        }}
      >
        {label}
      </span>
      <div className="aios-file-row__body">
        <div className="aios-file-row__name">{filename}</div>
        {preview && <div className="aios-file-row__preview">{preview}</div>}
        {domains && domains.length > 0 && (
          <div className="aios-file-row__domains">
            {domains.map((d) => (
              <span key={d} className="aios-file-row__domain-tag">{d}</span>
            ))}
          </div>
        )}
      </div>
      <div className="aios-file-row__meta">
        {size && <span className="aios-file-row__size">{size}</span>}
        {modified && <span className="aios-file-row__modified">{modified}</span>}
      </div>
    </div>
  );
}
