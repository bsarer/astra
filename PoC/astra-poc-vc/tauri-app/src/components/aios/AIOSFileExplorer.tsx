import React, { useEffect, useState } from "react";

interface FileThumbnail {
  label: string;
  accent: string;
}

interface FileRecord {
  id: string;
  filename: string;
  path: string;
  type: string;
  category: string;
  size_bytes: number;
  size_label: string;
  modified_at: string;
  domains: string[];
  preview: string;
  thumbnail: FileThumbnail;
  raw_url: string;
}

interface FolderRecord {
  id: string;
  name: string;
  path: string;
  file_count: number;
  folder_count: number;
  modified_at: string;
}

interface Breadcrumb {
  name: string;
  path: string;
}

interface AIOSFileExplorerProps {
  title?: string;
  subtitle?: string;
  query?: string;
  category?: string;
  timeframe?: string;
  directory?: string;
  sort?: string;
}

interface FileListResponse {
  files: FileRecord[];
  folders: FolderRecord[];
  breadcrumbs: Breadcrumb[];
  current_directory: string;
}

interface ApiError {
  detail?: string;
}

const SORT_OPTIONS = [
  { id: "modified-desc", label: "Latest first" },
  { id: "modified-asc", label: "Oldest first" },
  { id: "name-asc", label: "Name A–Z" },
  { id: "type-asc", label: "By type" },
  { id: "size-desc", label: "Largest first" },
] as const;

type SortOption = (typeof SORT_OPTIONS)[number]["id"];

function normalizeSortOption(value: string | undefined): SortOption {
  const valid: SortOption[] = ["modified-desc", "modified-asc", "name-asc", "type-asc", "size-desc"];
  return valid.includes(value as SortOption) ? (value as SortOption) : "modified-desc";
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

function getFileAccent(type: string, thumbnailAccent: string): string {
  if (thumbnailAccent) return thumbnailAccent;
  const t = type.toLowerCase();
  if (t === "pdf") return "#ef4444";
  if (["image", "png", "jpg", "jpeg", "webp", "gif", "svg"].includes(t)) return "#a855f7";
  if (["video", "mp4", "mov", "avi", "mkv"].includes(t)) return "#3b82f6";
  if (["doc", "docx", "txt", "md", "rtf"].includes(t)) return "#06b6d4";
  if (["xls", "xlsx", "csv"].includes(t)) return "#22c55e";
  return "#64748b";
}

function sortFiles(records: FileRecord[], sortOption: SortOption) {
  return [...records].sort((a, b) => {
    if (sortOption === "name-asc") return a.filename.localeCompare(b.filename);
    if (sortOption === "type-asc") {
      const tm = a.type.localeCompare(b.type);
      return tm !== 0 ? tm : a.filename.localeCompare(b.filename);
    }
    if (sortOption === "size-desc") return b.size_bytes - a.size_bytes;
    if (sortOption === "modified-asc") return a.modified_at.localeCompare(b.modified_at);
    return b.modified_at.localeCompare(a.modified_at);
  });
}

function sortFolders(records: FolderRecord[], sortOption: SortOption) {
  return [...records].sort((a, b) => {
    if (sortOption === "name-asc") return a.name.localeCompare(b.name);
    if (sortOption === "modified-asc") return a.modified_at.localeCompare(b.modified_at);
    return b.modified_at.localeCompare(a.modified_at);
  });
}

async function parseJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

// ---- Icons ----

function FolderIcon({ active }: { active: boolean }) {
  return (
    <svg
      className="aios-folder-card__icon"
      viewBox="0 0 22 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M1 4a2 2 0 012-2h4.172a2 2 0 011.414.586L9.828 4H19a2 2 0 012 2v10a2 2 0 01-2 2H3a2 2 0 01-2-2V4z"
        fill={active ? "rgba(56,189,248,0.25)" : "rgba(100,116,139,0.18)"}
        stroke={active ? "#38bdf8" : "#475569"}
        strokeWidth="1.5"
      />
    </svg>
  );
}

// ---- Folder Card ----

interface FolderCardProps {
  name: string;
  path: string;
  fileCount?: number;
  modifiedAt?: string;
  active: boolean;
  root?: boolean;
  onOpen: (path: string) => void;
}

function FolderCard({ name, path, fileCount, modifiedAt, active, root = false, onOpen }: FolderCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      className={`aios-folder-card${active ? " is-active" : ""}${root ? " aios-folder-card--root" : ""}`}
      onClick={() => onOpen(path)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(path);
        }
      }}
    >
      <div className="aios-folder-card__icon-wrap">
        <FolderIcon active={active} />
      </div>
      <div className="aios-folder-card__body">
        <div className="aios-folder-card__title">{name}</div>
        <div className="aios-folder-card__meta">
          {fileCount !== undefined && (
            <span className="aios-folder-card__count">{fileCount} files</span>
          )}
          {modifiedAt && <span>{formatTimeLabel(modifiedAt)}</span>}
        </div>
      </div>
      {active && <div className="aios-folder-card__active-dot" />}
    </div>
  );
}

// ---- File Card ----

interface FileCardProps {
  file: FileRecord;
  active: boolean;
  onSelect: (path: string) => void;
}

function FileCard({ file, active, onSelect }: FileCardProps) {
  const accent = getFileAccent(file.type, file.thumbnail.accent);
  const typeLabel = file.thumbnail.label || file.type.toUpperCase();

  return (
    <div
      role="button"
      tabIndex={0}
      className={`aios-file-card${active ? " is-active" : ""}`}
      style={{ "--file-accent": accent } as React.CSSProperties}
      onClick={() => onSelect(file.path)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(file.path);
        }
      }}
    >
      <div className="aios-file-card__accent-bar" />
      <div className="aios-file-card__content">
        <div className="aios-file-card__top-row">
          <span
            className="aios-file-card__type-badge"
            style={{
              color: accent,
              borderColor: `${accent}55`,
              background: `${accent}18`,
            }}
          >
            {typeLabel}
          </span>
          <div className="aios-file-card__actions">
            <span className="aios-file-card__size">{file.size_label}</span>
          </div>
        </div>
        <div className="aios-file-card__name">{file.filename}</div>
        <div className="aios-file-card__time">{formatTimeLabel(file.modified_at)}</div>
      </div>
    </div>
  );
}

// ---- Main Export ----

export function AIOSFileExplorer({
  title = "File System",
  query = "",
  category = "all",
  timeframe = "all time",
  directory = "",
  sort = "modified-desc",
}: AIOSFileExplorerProps) {
  const [activeDirectory, setActiveDirectory] = useState(directory);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [folders, setFolders] = useState<FolderRecord[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ name: "Files", path: "" }]);
  const [activePath, setActivePath] = useState("");
  const [sortOption, setSortOption] = useState<SortOption>(normalizeSortOption(sort));
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState("");

  const visibleFiles = sortFiles(files, sortOption);
  const visibleFolders = sortFolders(folders, sortOption);

  async function loadFiles(
    nextQuery = query,
    nextCategory = category,
    nextTimeframe = timeframe,
    nextDirectory = activeDirectory,
  ) {
    setLoadingFiles(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (nextQuery.trim()) params.set("query", nextQuery.trim());
      if (nextCategory !== "all") params.set("category", nextCategory);
      if (nextTimeframe !== "all time") params.set("timeframe", nextTimeframe);
      if (nextDirectory) params.set("subdirectory", nextDirectory);

      const resp = await fetch(`/api/files?${params.toString()}`);
      const data = await parseJson<FileListResponse & ApiError>(resp);
      if (!resp.ok) throw new Error(data.detail || "Unable to load files");

      const nextFiles = data.files || [];
      const nextFolders = data.folders || [];
      setFiles(nextFiles);
      setFolders(nextFolders);
      setBreadcrumbs(data.breadcrumbs || [{ name: "Files", path: "" }]);
      setActiveDirectory(data.current_directory || nextDirectory);
      setActivePath((cur) => {
        if (cur && nextFiles.some((file) => file.path === cur)) return cur;
        return "";
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load files");
      setFiles([]);
      setFolders([]);
    } finally {
      setLoadingFiles(false);
    }
  }

  useEffect(() => {
    setSortOption(normalizeSortOption(sort));
    setActiveDirectory(directory);
    void loadFiles(query, category, timeframe, directory);
  }, [query, category, timeframe, directory, sort]);

  function openDirectory(path: string) {
    setActiveDirectory(path);
    void loadFiles(query, category, timeframe, path);
  }

  const activeFile = files.find((file) => file.path === activePath) || null;

  return (
    <div className="aios-file-explorer">
      {/* Header */}
      <div className="aios-file-explorer__header">
        <div className="aios-file-explorer__header-left">
          <div className="aios-file-explorer__title">{title}</div>
          <div className="aios-file-explorer__path-label">
            /{activeDirectory ? ` ${activeDirectory}` : ""}
          </div>
        </div>
        <div className="aios-file-explorer__header-right">
          {loadingFiles ? (
            <span className="aios-file-explorer__badge aios-file-explorer__badge--syncing">
              <span className="aios-file-explorer__badge-dot" />
              Syncing
            </span>
          ) : (
            <span className="aios-file-explorer__stat">
              {visibleFiles.length} files · {visibleFolders.length} folders
            </span>
          )}
          <select
            className="aios-file-explorer__sort-select"
            value={sortOption}
            onChange={(e) => setSortOption(normalizeSortOption(e.target.value))}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Breadcrumbs */}
      <nav className="aios-file-explorer__breadcrumbs" aria-label="Directory navigation">
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={`${crumb.path}-${i}`}>
            {i > 0 && <span className="aios-file-explorer__crumb-sep" aria-hidden>›</span>}
            <button
              className={`aios-file-explorer__crumb${activeDirectory === crumb.path ? " is-active" : ""}`}
              onClick={() => openDirectory(crumb.path)}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        ))}
      </nav>

      {/* Error */}
      {error ? <div className="aios-file-explorer__error" role="alert">{error}</div> : null}

      {/* Body */}
      <div className="aios-file-explorer__layout">
        {/* Folders sidebar */}
        <aside className="aios-file-explorer__folders-panel">
          <div className="aios-file-explorer__panel-label">Folders</div>
          <FolderCard
            name="My Files"
            path=""
            active={activeDirectory === ""}
            root
            onOpen={openDirectory}
          />
          {visibleFolders.length === 0 && !loadingFiles ? (
            <div className="aios-file-explorer__panel-empty">No subfolders</div>
          ) : null}
          {visibleFolders.map((folder) => (
            <FolderCard
              key={folder.id || folder.path}
              name={folder.name}
              path={folder.path}
              fileCount={folder.file_count}
              modifiedAt={folder.modified_at}
              active={activeDirectory === folder.path}
              onOpen={openDirectory}
            />
          ))}
        </aside>

        {/* Files grid */}
        <main className="aios-file-explorer__files-panel">
          <div className="aios-file-explorer__panel-label">
            {activeDirectory ? activeDirectory : "All Files"}
            {visibleFiles.length > 0 && (
              <span className="aios-file-explorer__panel-count">{visibleFiles.length}</span>
            )}
          </div>
          <div className="aios-file-explorer__toolbar">
            <span className="aios-file-explorer__toolbar-text">
              {activeFile ? `Selected: ${activeFile.filename}` : "Click a file to select it"}
            </span>
          </div>
          {visibleFiles.length === 0 && !loadingFiles ? (
            <div className="aios-file-explorer__panel-empty">No files here.</div>
          ) : null}
          <div className="aios-file-explorer__grid">
            {visibleFiles.map((file) => (
              <FileCard
                key={file.id || file.path}
                file={file}
                active={activePath === file.path}
                onSelect={setActivePath}
              />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
