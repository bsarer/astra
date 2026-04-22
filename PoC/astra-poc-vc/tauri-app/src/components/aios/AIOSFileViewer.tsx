import React, { useEffect, useState } from "react";

type ViewerKind = "text" | "image" | "pdf";
type FileCategory = ViewerKind | "other";

interface FileViewerState {
  filename: string;
  path: string;
  kind: FileCategory;
  raw_url: string;
  size_label?: string;
  modified_at?: string;
  content?: string;
}

interface AIOSFileViewerProps {
  path?: string;
  filename?: string;
  preview_type?: ViewerKind;
  size_label?: string;
  modified_at?: string;
  raw_url?: string;
  viewer?: {
    kind?: ViewerKind;
    raw_url?: string;
  };
}

function encodeFilePath(path: string) {
  return path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

function formatTimeLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function inferKind(pathOrName: string, explicitKind?: ViewerKind): FileCategory {
  if (explicitKind) return explicitKind;
  const suffix = pathOrName.includes(".")
    ? pathOrName.slice(pathOrName.lastIndexOf(".")).toLowerCase()
    : "";
  if (suffix === ".md") return "text";
  if (suffix === ".pdf") return "pdf";
  if ([".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"].includes(suffix)) return "image";
  return "other";
}

function buildRawUrl(pathOrName?: string, rawUrl?: string): string {
  if (rawUrl) return rawUrl;
  if (!pathOrName) return "";
  return `/api/files/${encodeFilePath(pathOrName)}/raw`;
}

function buildInitialState(props: AIOSFileViewerProps): FileViewerState | null {
  const target = props.path?.trim() || props.filename?.trim() || "";
  const filename = props.filename?.trim() || target.split("/").pop() || "";
  const rawUrl = buildRawUrl(target, props.viewer?.raw_url || props.raw_url);
  if (!target || !filename || !rawUrl) {
    return null;
  }

  return {
    filename,
    path: target,
    kind: inferKind(target || filename, props.viewer?.kind || props.preview_type),
    raw_url: rawUrl,
    size_label: props.size_label,
    modified_at: props.modified_at,
  };
}

export function AIOSFileViewer(props: AIOSFileViewerProps) {
  const initialState = buildInitialState(props);
  const [file, setFile] = useState<FileViewerState | null>(initialState);
  const [loading, setLoading] = useState(Boolean(initialState?.kind === "text" && !initialState.content));
  const [error, setError] = useState("");

  useEffect(() => {
    const nextState = buildInitialState(props);
    if (!nextState) {
      setFile(null);
      setLoading(false);
      setError("No file path was provided.");
      return;
    }

    setFile(nextState);
    setError("");

    if (nextState.kind !== "text") {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    void (async () => {
      try {
        const resp = await fetch(nextState.raw_url);
        if (!resp.ok) throw new Error(`Unable to open file (${resp.status})`);
        const content = await resp.text();
        if (!cancelled) {
          setFile((current) => {
            if (!current) return current;
            return { ...current, content };
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to open file");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    props.filename,
    props.modified_at,
    props.path,
    props.preview_type,
    props.raw_url,
    props.size_label,
    props.viewer?.kind,
    props.viewer?.raw_url,
  ]);

  const viewerKind = file?.kind || "text";
  const rawUrl = file?.raw_url || "";
  const title = file?.filename || props.filename || "File viewer";
  const subheadParts = [file?.path || props.path || ""];
  if (file?.size_label) subheadParts.push(file.size_label);
  if (file?.modified_at) subheadParts.push(formatTimeLabel(file.modified_at));

  return (
    <div className="aios-file-viewer aios-file-viewer--embedded">
      <div className="aios-file-viewer__panel aios-file-viewer__panel--embedded">
        <div className="aios-file-viewer__header">
          <div className="aios-file-viewer__meta">
            <div className="aios-file-viewer__title">{title}</div>
            <div className="aios-file-viewer__subhead">
              {subheadParts.filter(Boolean).join(" · ")}
            </div>
          </div>
          <div className="aios-file-viewer__header-actions">
            {rawUrl ? (
              <a
                className="aios-file-viewer__link"
                href={rawUrl}
                target="_blank"
                rel="noreferrer"
              >
                Open raw
              </a>
            ) : null}
          </div>
        </div>
        <div className="aios-file-viewer__body">
          {loading ? (
            <div className="aios-file-viewer__status">Loading file…</div>
          ) : (
            <div className="aios-file-viewer__content">
              {error ? (
                <div className="aios-file-viewer__status aios-file-viewer__status--error">{error}</div>
              ) : null}
              {!error && viewerKind === "image" && rawUrl ? (
                <div className="aios-file-viewer__media-wrap">
                  <img className="aios-file-viewer__image" src={rawUrl} alt={title} />
                </div>
              ) : null}
              {!error && viewerKind === "pdf" && rawUrl ? (
                <iframe className="aios-file-viewer__frame" src={rawUrl} title={title} />
              ) : null}
              {!error && viewerKind === "text" ? (
                <div className="aios-file-viewer__text-wrap">
                  <pre className="aios-file-viewer__text">
                    {file?.content || "No file content available."}
                  </pre>
                </div>
              ) : null}
              {!error && viewerKind === "other" ? (
                <div className="aios-file-viewer__text-wrap">
                  <div className="aios-file-viewer__status">
                    No embedded renderer is available for this file type.
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
