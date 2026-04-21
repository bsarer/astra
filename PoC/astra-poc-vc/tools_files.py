"""
File system tools and metadata helpers for Astra's sandboxed file explorer.

Files live in data/personas/mike/files/ by default and can be overridden with
PERSONA_FILES_DIR. The helpers in this module are used both by LangChain tools
and the FastAPI file-management endpoints.
"""

from __future__ import annotations
from typing import Optional
import json
import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote
from langchain_core.tools import tool

logger = logging.getLogger("astra.files")

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".log"}
PDF_EXTENSIONS = {".pdf"}
_META_FILENAME = ".astra_meta.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
OFFICE_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | OFFICE_EXTENSIONS

STOP_WORDS = {
    "a", "about", "add", "all", "an", "and", "files", "find", "for", "from",
    "in", "into", "my", "of", "on", "show", "summarize", "that", "the", "these",
    "those", "to", "view", "with",
}
TEMPORAL_WORDS = {
    "today", "yesterday", "recent", "recently", "latest", "newest", "last",
    "week", "this", "month", "downloads", "downloaded",
}

ORGANIZATION_STRATEGY_ALIASES = {
    "type": "type",
    "category": "type",
    "categories": "type",
    "filetype": "type",
    "extension": "extension",
    "extensions": "extension",
    "name": "name",
    "names": "name",
    "alphabetical": "alphabetical",
    "alphabet": "alphabetical",
    "letter": "alphabetical",
    "meaning": "meaning",
    "meanings": "meaning",
    "domain": "meaning",
    "domains": "meaning",
    "topic": "meaning",
    "topics": "meaning",
    "semantic": "meaning",
}


def _resolve_base() -> Path:
    """Find the files directory, checking multiple locations."""
    env_override = os.getenv("PERSONA_FILES_DIR", "")
    candidates = [
        Path(env_override) if env_override else None,
        Path(__file__).parent / "data/personas/mike/files",
        Path("/app/data/personas/mike/files"),
        Path("data/personas/mike/files"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists() and candidate.is_dir():
            return candidate
    return Path(__file__).parent / "data/personas/mike/files"


def _safe_relative_path(base: Path, relative_path: str) -> Path:
    """Resolve a user-provided relative path and keep it inside the sandbox."""
    base_resolved = base.resolve()
    candidate = (base / relative_path).resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise ValueError("Path escapes the sandboxed file directory")
    return candidate


def _supported_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _safe_relative_str(base: Path, path: Path) -> str:
    relative = path.relative_to(base)
    return "" if str(relative) == "." else str(relative)


def _resolve_user_file(path_or_name: str, *, extensions: Optional[set[str]] = None) -> Path:
    """Resolve a relative path or fuzzy filename to a supported file in the sandbox."""
    base = _resolve_base()
    allowed_extensions = extensions or SUPPORTED_EXTENSIONS
    direct_candidates: list[Path] = []
    for value in (path_or_name, Path(path_or_name).name):
        try:
            direct_candidates.append(_safe_relative_path(base, value))
        except ValueError:
            continue

    for candidate in direct_candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in allowed_extensions:
            return candidate

    search_term = Path(path_or_name).stem.lower()
    for path in _iter_files(base=base):
        if path.suffix.lower() not in allowed_extensions:
            continue
        if search_term and search_term in path.stem.lower():
            return path

    raise FileNotFoundError(path_or_name)


def _guess_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return "documents"
    if suffix in OFFICE_EXTENSIONS:
        return "documents"
    if suffix in TEXT_EXTENSIONS:
        return "documents"
    if suffix in IMAGE_EXTENSIONS:
        return "images"
    if suffix in VIDEO_EXTENSIONS:
        return "videos"
    return "other"


def _format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _tool_response(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2)


def _tokenize_query(query: str) -> list[str]:
    terms = re.findall(r"[a-z0-9]+", query.lower())
    return [
        term for term in terms
        if len(term) > 1 and term not in STOP_WORDS and term not in TEMPORAL_WORDS
    ]


# ---------------------------------------------------------------------------
# Episodic memory hooks — non-blocking, best-effort
# ---------------------------------------------------------------------------

def _store_file_episode(filename: str, action: str, extra: str = "") -> None:
    """Record a file workflow event in memory. Never raises."""
    try:
        from memory import get_memory_manager
        content = f"File '{filename}' was {action}."
        if extra:
            content += f" {extra}"
        get_memory_manager().store(
            content, memory_type="episode", tags=["file_workflow", action]
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Metadata sidecar — persists tags/domains per directory
# ---------------------------------------------------------------------------

def _meta_path(file_path: Path) -> Path:
    return file_path.parent / _META_FILENAME


def _load_file_meta(file_path: Path) -> dict[str, Any]:
    """Load persisted metadata for a single file."""
    meta_file = _meta_path(file_path)
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get(file_path.name, {})
    except Exception:
        return {}


def _save_file_meta(file_path: Path, data: dict[str, Any]) -> None:
    """Persist metadata for a single file into the directory sidecar."""
    meta_file = _meta_path(file_path)
    try:
        all_meta: dict[str, Any] = {}
        if meta_file.exists():
            try:
                all_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                all_meta = {}
        all_meta[file_path.name] = {**all_meta.get(file_path.name, {}), **data}
        meta_file.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")
    except Exception:
        pass


def _infer_image_tags(path: Path) -> list[str]:
    name = path.stem.replace("_", " ").replace("-", " ").lower()
    tokens = [token for token in name.split() if token and token not in STOP_WORDS]
    return tokens[:5]


def _file_domains(path: Path, preview_text: str) -> list[str]:
    from domain_router import classify

    return classify(f"{path.name} {preview_text[:300]}").domains


def _build_summary_payload(path: Path) -> dict[str, Any]:
    category = _guess_category(path)
    if category == "images":
        tags = _infer_image_tags(path)
        summary = [
            f"Image asset named {path.stem.replace('_', ' ').replace('-', ' ')}",
            "Preview is available in the explorer panel.",
        ]
        if tags:
            summary.append(f"Suggested tags: {', '.join(tags[:3])}")
        return {"summary": summary[:3], "tags": tags}

    if category == "videos":
        return {
            "summary": [
                f"Video asset: {path.name}",
                "Preview is available as a downloadable asset.",
            ],
            "tags": [],
        }

    file_label = path.stem.replace("_", " ").replace("-", " ")
    extension_tag = path.suffix.lower().lstrip(".")
    return {
        "summary": [
            f"Document file: {file_label}",
            "Open the raw file to inspect its contents.",
        ],
        "tags": [extension_tag] if extension_tag else [],
    }


def _file_record(path: Path, base: Optional[Path] = None) -> dict[str, Any]:
    base = base or _resolve_base()
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()
    created_at = datetime.fromtimestamp(stat.st_ctime).astimezone().isoformat()
    category = _guess_category(path)
    preview_payload = _build_summary_payload(path)
    relative_path = _safe_relative_str(base, path)
    raw_path = "/".join(quote(part, safe="") for part in Path(relative_path).parts)
    preview_text = " ".join(preview_payload["summary"])
    domains = _file_domains(path, preview_text)
    thumb_accent = {
        "documents": "#38bdf8",
        "images": "#f59e0b",
        "videos": "#f97316",
        "other": "#94a3b8",
    }[category]
    record = {
        "id": relative_path,
        "filename": path.name,
        "path": relative_path,
        "type": path.suffix.lower().lstrip("."),
        "category": category,
        "size_bytes": stat.st_size,
        "size_kb": round(stat.st_size / 1024, 1),
        "size_label": _format_bytes(stat.st_size),
        "modified_at": modified_at,
        "created_at": created_at,
        "domains": domains,
        "preview": "\n".join(preview_payload["summary"][:2]),
        "summary_points": preview_payload["summary"],
        "tags": preview_payload["tags"],
        "thumbnail": {
            "label": path.suffix.upper().lstrip(".") or "FILE",
            "accent": thumb_accent,
        },
        "raw_url": f"/api/files/{raw_path}/raw",
    }
    # Merge persisted tags/domains from the metadata sidecar (Feature 7)
    saved_meta = _load_file_meta(path)
    if saved_meta.get("tags"):
        record["tags"] = list({*record["tags"], *saved_meta["tags"]})
    if saved_meta.get("domains"):
        record["domains"] = list({*record["domains"], *saved_meta["domains"]})
    return record


def _folder_record(path: Path, base: Optional[Path] = None) -> dict[str, Any]:
    base = base or _resolve_base()
    relative_path = _safe_relative_str(base, path)
    file_count = sum(1 for file_path in path.rglob("*") if _supported_file(file_path))
    folder_count = sum(1 for folder_path in path.iterdir() if folder_path.is_dir()) if path.exists() else 0
    stat = path.stat()
    return {
        "id": relative_path or "root",
        "name": path.name if relative_path else "Files",
        "path": relative_path,
        "file_count": file_count,
        "folder_count": folder_count,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
    }


def _breadcrumbs(base: Path, subdirectory: str = "") -> list[dict[str, str]]:
    crumbs = [{"name": "Files", "path": ""}]
    current = _safe_relative_path(base, subdirectory) if subdirectory else base
    relative = _safe_relative_str(base, current)
    if not relative:
        return crumbs
    parts = Path(relative).parts
    running = []
    for part in parts:
        running.append(part)
        crumbs.append({"name": part, "path": str(Path(*running))})
    return crumbs


def _iter_files(base: Optional[Path] = None, subdirectory: str = "", recursive: bool = True) -> list[Path]:
    base = base or _resolve_base()
    target = _safe_relative_path(base, subdirectory) if subdirectory else base
    if not target.exists():
        return []
    iterator = target.rglob("*") if recursive else target.iterdir()
    return sorted(
        (path for path in iterator if _supported_file(path)),
        key=lambda path: path.name.lower(),
    )


def _iter_folders(base: Optional[Path] = None, subdirectory: str = "") -> list[Path]:
    base = base or _resolve_base()
    target = _safe_relative_path(base, subdirectory) if subdirectory else base
    if not target.exists():
        return []
    return sorted((path for path in target.iterdir() if path.is_dir()), key=lambda path: path.name.lower())


def _timeframe_window(timeframe: str, now: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime], str]:
    value = timeframe.lower().strip()
    current = now or datetime.now().astimezone()
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if not value:
        return None, None, "all time"
    if "yesterday" in value:
        start = day_start - timedelta(days=1)
        return start, day_start, "yesterday"
    if "today" in value:
        return day_start, day_start + timedelta(days=1), "today"
    if "last week" in value:
        return current - timedelta(days=7), current, "last 7 days"
    if "this week" in value:
        return day_start - timedelta(days=day_start.weekday()), current, "this week"
    if "last month" in value:
        return current - timedelta(days=30), current, "last 30 days"
    if any(term in value for term in ("recent", "recently", "latest", "newest")):
        return current - timedelta(days=14), current, "recent"
    return None, None, "all time"


def _matches_timeframe(path: Path, timeframe: str) -> bool:
    start, end, _ = _timeframe_window(timeframe)
    if start is None and end is None:
        return True
    modified_at = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    if start and modified_at < start:
        return False
    if end and modified_at >= end:
        return False
    return True


def _collect_file_records(
    *,
    subdirectory: str = "",
    query: str = "",
    category: str = "all",
    timeframe: str = "",
    limit: Optional[int] = None,
    recursive: bool = True,
) -> list[dict[str, Any]]:
    base = _resolve_base()
    terms = _tokenize_query(query)
    records = []

    for path in _iter_files(base=base, subdirectory=subdirectory, recursive=recursive):
        current_category = _guess_category(path)
        if category != "all" and current_category != category:
            continue
        if timeframe and not _matches_timeframe(path, timeframe):
            continue

        record = _file_record(path, base=base)
        search_blob = " ".join(
            [
                record["filename"].lower(),
                record["preview"].lower(),
                " ".join(record["domains"]).lower(),
                " ".join(record["tags"]).lower(),
            ]
        )
        if terms and not all(term in search_blob for term in terms):
            continue
        records.append(record)

    sort_recent = timeframe and _timeframe_window(timeframe)[2] == "recent"
    records.sort(
        key=lambda record: record["modified_at"],
        reverse=bool(sort_recent or "recent" in query.lower() or "latest" in query.lower()),
    )

    if limit is not None:
        return records[:limit]
    return records


def list_folder_records(subdirectory: str = "") -> list[dict[str, Any]]:
    base = _resolve_base()
    return [_folder_record(path, base=base) for path in _iter_folders(base=base, subdirectory=subdirectory)]


def build_file_listing_payload(
    *,
    files: list[dict[str, Any]],
    folders: list[dict[str, Any]],
    subdirectory: str = "",
    query: str = "",
    category: str = "all",
    timeframe: str = "",
) -> dict[str, Any]:
    base = _resolve_base()
    return {
        "files": files,
        "folders": folders,
        # `count` is total visible items so callers do not mistake file count for the
        # entire directory inventory when folders are present.
        "count": len(files) + len(folders),
        "file_count": len(files),
        "folder_count": len(folders),
        "filters": {
            "subdirectory": subdirectory,
            "query": query,
            "category": category,
            "timeframe": _timeframe_window(timeframe)[2] if timeframe else "all time",
        },
        "current_directory": subdirectory,
        "current_directory_label": subdirectory or "Files",
        "breadcrumbs": _breadcrumbs(base, subdirectory=subdirectory),
    }


def open_user_file_data(path_or_name: str) -> dict[str, Any]:
    candidate = _resolve_user_file(path_or_name)
    return _build_preview_payload(candidate, _resolve_base())


def preview_user_file_data(filename: str) -> dict[str, Any]:
    return open_user_file_data(filename)


def _build_preview_payload(path: Path, base: Optional[Path] = None) -> dict[str, Any]:
    base = base or _resolve_base()
    record = _file_record(path, base=base)
    preview_type = "text"
    if record["category"] == "images":
        preview_type = "image"
    elif record["type"] == "pdf":
        preview_type = "pdf"
    elif record["category"] == "videos":
        preview_type = "video"

    content = record["preview"] if preview_type == "text" else ""
    viewer = {
        "kind": preview_type,
        "raw_url": record["raw_url"],
        "content": content,
        "content_truncated": False,
    }

    return {
        **record,
        "preview_type": preview_type,
        "content": content,
        "content_truncated": False,
        "viewer": viewer,
        "summary_card": {
            "headline": f"{record['filename']} · {record['category']}",
            "points": record["summary_points"],
            "domains": record["domains"],
        },
        "analysis": {
            "classification": record["category"],
            "tags": record["tags"],
            "domains": record["domains"],
        },
        "actions": [
            {"id": "rename", "label": "Rename"},
            {"id": "move", "label": "Organize"},
            {"id": "delete", "label": "Delete"},
        ],
    }


def _dedupe_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _record_search_blob(record: dict[str, Any]) -> str:
    return " ".join(
        [
            record.get("filename", ""),
            record.get("preview", ""),
            " ".join(record.get("summary_points", [])),
            " ".join(record.get("tags", [])),
            " ".join(record.get("domains", [])),
        ]
    ).lower()


def _normalize_organization_strategy(value: str) -> str:
    normalized = re.sub(r"[^a-z]+", "", value.lower())
    if not normalized:
        return "type"
    if normalized not in ORGANIZATION_STRATEGY_ALIASES:
        allowed = ", ".join(sorted(set(ORGANIZATION_STRATEGY_ALIASES.values())))
        raise ValueError(f"Unsupported organization strategy: {value}. Use one of: {allowed}")
    return ORGANIZATION_STRATEGY_ALIASES[normalized]


def _sanitize_bucket_name(value: str) -> str:
    cleaned = re.sub(r"[\\/]+", " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(".")
    return cleaned or "Other"


def _name_bucket_token(filename: str) -> str:
    stem = Path(filename).stem
    tokens = re.split(r"[^A-Za-z0-9]+", stem)
    for token in tokens:
        if token and token.lower() not in STOP_WORDS:
            return token
    return stem or "Other"


def _category_bucket_name(category: str) -> str:
    return {
        "documents": "Documents",
        "images": "Images",
        "videos": "Videos",
        "other": "Other",
    }.get(category, "Other")


def _bucket_name_for_record(record: dict[str, Any], strategy: str) -> str:
    if strategy == "type":
        return _category_bucket_name(record.get("category", "other"))

    if strategy == "extension":
        extension = str(record.get("type", "")).strip().upper()
        return _sanitize_bucket_name(extension or "Other")

    if strategy == "name":
        token = _name_bucket_token(record.get("filename", ""))
        return _sanitize_bucket_name(token[:40])

    if strategy == "alphabetical":
        token = _name_bucket_token(record.get("filename", ""))
        first = token[:1].upper()
        if first.isalpha():
            return first
        if first.isdigit():
            return "0-9"
        return "Other"

    if strategy == "meaning":
        domains = record.get("domains", []) or []
        primary = str(domains[0]) if domains else "other"
        return _sanitize_bucket_name(primary.replace("_", " ").title())

    return "Other"


def categorize_user_files_data(
    group_by: str = "type",
    *,
    subdirectory: str = "",
    destination_subdirectory: str = "",
    recursive: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Organize files into folders by strategy and return a move summary."""
    base = _resolve_base()
    strategy = _normalize_organization_strategy(group_by)
    source_dir = _safe_relative_path(base, subdirectory) if subdirectory else base
    destination_root = _safe_relative_path(base, destination_subdirectory) if destination_subdirectory else source_dir

    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(subdirectory or "Files")

    file_paths = _iter_files(base=base, subdirectory=subdirectory, recursive=recursive)
    created_folders: set[str] = set()
    grouped_counts: dict[str, int] = {}
    planned: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for path in file_paths:
        record = _file_record(path, base=base)
        bucket = _bucket_name_for_record(record, strategy)
        target_dir = destination_root / bucket
        target_relative = _safe_relative_str(base, target_dir)

        if path.parent.resolve() == target_dir.resolve():
            skipped.append({
                "path": record["path"],
                "reason": "already_in_target_folder",
                "folder": target_relative or bucket,
            })
            continue

        destination = _dedupe_destination(target_dir / path.name)
        planned.append({
            "path": record["path"],
            "filename": record["filename"],
            "folder": target_relative or bucket,
            "moved_to": _safe_relative_str(base, destination),
        })
        created_folders.add(target_relative or bucket)
        grouped_counts[bucket] = grouped_counts.get(bucket, 0) + 1

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
            _store_file_episode(record["filename"], "categorized", f"Strategy: {strategy}; Folder: {bucket}")

    return {
        "group_by": strategy,
        "source": subdirectory or "root",
        "destination_root": _safe_relative_str(base, destination_root) or "root",
        "recursive": recursive,
        "dry_run": dry_run,
        "moved_count": len(planned),
        "skipped_count": len(skipped),
        "created_folder_count": len(created_folders),
        "groups": grouped_counts,
        "created_folders": sorted(created_folders),
        "moved": planned,
        "skipped": skipped,
    }


def rename_user_file_data(path: str, new_name: str) -> dict[str, Any]:
    base = _resolve_base()
    source = _safe_relative_path(base, path)
    if not source.exists() or not _supported_file(source):
        raise FileNotFoundError(path)
    sanitized_name = Path(new_name).name.strip()
    if not sanitized_name:
        raise ValueError("New filename is required")
    destination = source.with_name(sanitized_name)
    if destination.exists():
        raise ValueError("A file with that name already exists")
    source.rename(destination)
    _store_file_episode(source.name, "renamed", f"New name: {sanitized_name}")
    return _build_preview_payload(destination, base)


def move_user_file_data(path: str, destination_subdirectory: str) -> dict[str, Any]:
    base = _resolve_base()
    source = _safe_relative_path(base, path)
    if source.is_dir():
        raise ValueError(
            f"'{path}' is a folder, not a file. "
            "Use move_multiple_files with individual file paths inside it."
        )
    if not source.exists() or not _supported_file(source):
        raise FileNotFoundError(path)
    relative_target = destination_subdirectory.strip().strip("/")
    destination_dir = base if not relative_target else _safe_relative_path(base, relative_target)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = _dedupe_destination(destination_dir / source.name)
    source.rename(destination)
    _store_file_episode(source.name, "moved", f"Destination: {destination_subdirectory}")
    return _build_preview_payload(destination, base)


def create_folder_data(name: str, parent_subdirectory: str = "") -> dict[str, Any]:
    base = _resolve_base()
    sanitized_name = Path(name).name.strip()
    if not sanitized_name:
        raise ValueError("Folder name is required")
    parent = _safe_relative_path(base, parent_subdirectory) if parent_subdirectory else base
    destination = parent / sanitized_name
    destination_resolved = destination.resolve()
    if destination_resolved != base.resolve() and base.resolve() not in destination_resolved.parents:
        raise ValueError("Folder escapes the sandboxed file directory")
    if destination.exists():
        raise ValueError("A folder with that name already exists")
    destination.mkdir(parents=True, exist_ok=False)
    return _folder_record(destination, base)


def delete_user_folder_data(path: str, recursive: bool = True) -> dict[str, Any]:
    base = _resolve_base()
    relative_target = path.strip().strip("/")
    if not relative_target:
        raise ValueError("Refusing to delete the root files directory")

    target = _safe_relative_path(base, relative_target)
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError(path)

    file_count = sum(1 for child in target.rglob("*") if child.is_file())
    folder_count = sum(1 for child in target.rglob("*") if child.is_dir())

    if recursive:
        shutil.rmtree(target)
    else:
        try:
            target.rmdir()
        except OSError as exc:
            raise ValueError("Folder is not empty; retry with recursive delete enabled") from exc

    return {
        "deleted": True,
        "path": relative_target,
        "recursive": recursive,
        "deleted_file_count": file_count,
        "deleted_folder_count": folder_count + 1,
    }


def delete_user_file_data(path: str) -> dict[str, Any]:
    base = _resolve_base()
    target = _safe_relative_path(base, path)
    if not target.exists() or not _supported_file(target):
        raise FileNotFoundError(path)
    _store_file_episode(target.name, "deleted")
    target.unlink()
    return {"deleted": True, "path": path}


def delete_multiple_files_data(paths: list[str]) -> dict[str, Any]:
    """Delete multiple files in one operation and report partial failures."""
    base = _resolve_base()
    deleted: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for path in paths:
        try:
            target = _safe_relative_path(base, path)
            if target.is_dir():
                errors.append({"path": path, "error": f"'{path}' is a folder, not a file"})
                continue
            if not target.exists() or not _supported_file(target):
                errors.append({"path": path, "error": f"File not found: {path}"})
                continue
            _store_file_episode(target.name, "deleted")
            target.unlink()
            deleted.append({"path": path})
        except Exception as exc:
            errors.append({"path": path, "error": f"{type(exc).__name__}: {exc}"})

    return {
        "deleted_count": len(deleted),
        "error_count": len(errors),
        "deleted": deleted,
        "errors": errors,
    }


def save_binary_file_data(filename: str, content: bytes, destination_subdirectory: str = "Downloads") -> dict[str, Any]:
    base = _resolve_base()
    safe_name = Path(filename).name.strip()
    if not safe_name:
        raise ValueError("Filename is required")

    destination_subdirectory = destination_subdirectory.strip().strip("/")
    destination_dir = base if not destination_subdirectory else _safe_relative_path(base, destination_subdirectory)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = _dedupe_destination(destination_dir / safe_name)
    destination.write_bytes(content)
    _store_file_episode(safe_name, "saved", f"Destination: {destination_subdirectory}")
    # Auto-tag: compute and persist metadata without reading file contents.
    try:
        from domain_router import classify
        summary_payload = _build_summary_payload(destination)
        computed_domains = classify(f"{safe_name} {' '.join(summary_payload['summary'])}").domains
        _save_file_meta(destination, {
            "tags": summary_payload["tags"],
            "domains": computed_domains,
            "indexed_at": datetime.now().astimezone().isoformat(),
        })
    except Exception:
        pass
    return _build_preview_payload(destination, base)



@tool
def list_user_files(
    subdirectory: str = "",
    query: str = "",
    category: str = "all",
    timeframe: str = "",
) -> str:
    """List files in Mike's sandboxed file system with metadata and light previews.

    Always lists files recursively across all subdirectories. An empty subdirectory
    means the root "Files" directory. When the user says "files", "my files", or
    "all my files" without naming a folder, leave subdirectory empty — files from
    all nested folders will be included automatically.

    Use query for semantic intent like "pricing", "recent files", or "downloaded yesterday".
    Category supports all/documents/images/videos. Timeframe supports today/yesterday/recent.
    """
    base = _resolve_base()
    if subdirectory:
        try:
            _safe_relative_path(base, subdirectory)
        except ValueError as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {str(exc)}", "files": []})

    applied_timeframe = timeframe or query
    files = _collect_file_records(
        subdirectory=subdirectory,
        query=query,
        category=category,
        timeframe=applied_timeframe,
        recursive=True,
    )
    folders = list_folder_records(subdirectory=subdirectory)
    payload = build_file_listing_payload(
        files=files,
        folders=folders,
        subdirectory=subdirectory,
        query=query,
        category=category,
        timeframe=applied_timeframe,
    )
    return json.dumps(payload, indent=2)


@tool
def search_user_files(query: str) -> str:
    """Search Mike's files by topic, file type, or timeframe-sensitive query.

    Search always runs across Mike's files. If the user says only "files" or
    "my files", prefer list_user_files() for the root directory instead of this tool.

    Examples: "Acme pricing", "travel notes", "files from yesterday", "recent documents".
    """
    from domain_router import classify

    domains = classify(query).domains
    category = "all"
    query_lower = query.lower()
    if "image" in query_lower or "photo" in query_lower:
        category = "images"
    elif "video" in query_lower:
        category = "videos"
    elif "doc" in query_lower or "pdf" in query_lower or "note" in query_lower:
        category = "documents"

    results = _collect_file_records(query=query, category=category, timeframe=query, limit=8)
    if not results:
        return json.dumps({"message": f"No files found matching '{query}'", "results": []})

    return json.dumps(
        {
            "query": query,
            "domains_searched": domains,
            "filters": {
                "category": category,
                "timeframe": _timeframe_window(query)[2],
            },
            "results": results,
        },
        indent=2,
    )


@tool
def open_user_file(filename: str) -> str:
    """Open a file inside Astra and return viewer-ready metadata for text, PDF, image, or video files."""
    try:
        return _tool_response(open_user_file_data(filename))
    except FileNotFoundError:
        return _tool_response({"error": f"File not found: {filename}"})



@tool
def create_user_folder(name: str, parent_subdirectory: str = "") -> str:
    """Create a folder in Mike's sandboxed file system."""
    try:
        return _tool_response(create_folder_data(name, parent_subdirectory))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def delete_user_folder(path: str, recursive: bool = True) -> str:
    """Delete a folder from Mike's sandboxed file system."""
    try:
        return _tool_response(delete_user_folder_data(path, recursive=recursive))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def rename_user_file(path: str, new_name: str) -> str:
    """Rename a file in Mike's sandboxed file system."""
    try:
        return _tool_response(rename_user_file_data(path, new_name))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def move_user_file(path: str, destination_subdirectory: str) -> str:
    """Move a single file into another folder in Mike's sandboxed file system.

    path: relative path to the file (e.g. "Sales & Pipeline/Q1_Report.md").
    destination_subdirectory: target folder (e.g. "Team & Operations"). Empty string = root.
    If a file with the same name already exists at the destination, a suffix is appended automatically.
    To move all files from a folder in one call, use move_multiple_files instead.
    """
    try:
        return _tool_response(move_user_file_data(path, destination_subdirectory))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


def move_multiple_files_data(
    paths: list[str], destination_subdirectory: str
) -> dict[str, Any]:
    """Move multiple files to the same destination folder in one operation."""
    base = _resolve_base()
    relative_target = destination_subdirectory.strip().strip("/")
    destination_dir = base if not relative_target else _safe_relative_path(base, relative_target)
    destination_dir.mkdir(parents=True, exist_ok=True)

    moved: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in paths:
        try:
            source = _safe_relative_path(base, path)
            if source.is_dir():
                errors.append({"path": path, "error": f"'{path}' is a folder, not a file"})
                continue
            if not source.exists() or not _supported_file(source):
                errors.append({"path": path, "error": f"File not found: {path}"})
                continue
            destination = _dedupe_destination(destination_dir / source.name)
            source.rename(destination)
            _store_file_episode(source.name, "moved", f"Destination: {destination_subdirectory}")
            moved.append({"path": path, "moved_to": _safe_relative_str(base, destination)})
        except Exception as exc:
            errors.append({"path": path, "error": f"{type(exc).__name__}: {exc}"})

    return {
        "destination": destination_subdirectory or "root",
        "moved_count": len(moved),
        "error_count": len(errors),
        "moved": moved,
        "errors": errors,
    }


def move_files_in_folder_data(
    source_subdirectory: str,
    destination_subdirectory: str = "",
    recursive: bool = False,
) -> dict[str, Any]:
    """Move all supported files from one folder into another folder."""
    base = _resolve_base()
    source_relative = source_subdirectory.strip().strip("/")
    if not source_relative:
        raise ValueError("Source folder is required")

    source_dir = _safe_relative_path(base, source_relative)
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(source_subdirectory)

    destination_relative = destination_subdirectory.strip().strip("/")
    destination_dir = base if not destination_relative else _safe_relative_path(base, destination_relative)
    if source_dir == destination_dir:
        raise ValueError("Source and destination folders are the same")

    paths = [
        _safe_relative_str(base, path)
        for path in _iter_files(base=base, subdirectory=source_relative, recursive=recursive)
    ]
    if not paths:
        return {
            "source": source_relative,
            "destination": destination_relative or "root",
            "recursive": recursive,
            "moved_count": 0,
            "error_count": 0,
            "moved": [],
            "errors": [],
        }

    result = move_multiple_files_data(paths, destination_relative)
    result["source"] = source_relative
    result["recursive"] = recursive
    return result


@tool
def move_multiple_files(paths: list[str], destination_subdirectory: str) -> str:
    """Move multiple files to the same destination folder in a single call.

    Use this instead of calling move_user_file repeatedly — it avoids hitting
    the agent iteration limit when relocating many files at once.

    paths: list of relative file paths (e.g. ["Sales & Pipeline/Q1_Report.md", ...]).
    destination_subdirectory: target folder (e.g. "Team & Operations"). Empty = root.
    Name conflicts are resolved automatically by appending a numeric suffix.
    """
    try:
        return _tool_response(move_multiple_files_data(paths, destination_subdirectory))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def move_files_in_folder(
    source_subdirectory: str,
    destination_subdirectory: str = "",
    recursive: bool = False,
) -> str:
    """Move all supported files from one folder into another folder in a single call.

    Use this when the user says things like:
    - "move files inside Physics & Labs to root"
    - "move everything from Downloads into Team & Operations"
    """
    try:
        return _tool_response(
            move_files_in_folder_data(
                source_subdirectory,
                destination_subdirectory=destination_subdirectory,
                recursive=recursive,
            )
        )
    except FileNotFoundError:
        return _tool_response({"error": f"Folder not found: {source_subdirectory}"})
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def categorize_user_files(
    group_by: str = "type",
    subdirectory: str = "",
    destination_subdirectory: str = "",
    recursive: bool = True,
    dry_run: bool = False,
) -> str:
    """Organize files into folders by type, extension, name, alphabetical bucket, or meaning.

    group_by:
    - "type": Documents / Images / Videos / Other
    - "extension": PDF / PNG / MD / ...
    - "name": first meaningful token in the filename, e.g. "Acme", "Helsinki"
    - "alphabetical": A / B / C / 0-9 / Other
    - "meaning": primary semantic domain, e.g. Sales / Travel / Finance

    Use dry_run=True to preview the plan without moving files.
    """
    try:
        return _tool_response(
            categorize_user_files_data(
                group_by,
                subdirectory=subdirectory,
                destination_subdirectory=destination_subdirectory,
                recursive=recursive,
                dry_run=dry_run,
            )
        )
    except FileNotFoundError:
        return _tool_response({"error": f"Folder not found: {subdirectory or 'Files'}"})
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def delete_user_file(path: str) -> str:
    """Delete a file from Mike's sandboxed file system."""
    try:
        return _tool_response(delete_user_file_data(path))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})


@tool
def delete_multiple_files(paths: list[str]) -> str:
    """Delete multiple files in a single call.

    Use this when the user asks to delete several files at once instead of
    looping over `delete_user_file`.
    """
    try:
        return _tool_response(delete_multiple_files_data(paths))
    except Exception as exc:
        return _tool_response({"error": f"{type(exc).__name__}: {str(exc)}"})



file_tools = [
    list_user_files,
    open_user_file,
    search_user_files,
    create_user_folder,
    delete_user_folder,
    rename_user_file,
    move_user_file,
    move_multiple_files,
    move_files_in_folder,
    categorize_user_files,
    delete_user_file,
    delete_multiple_files,
]


def index_all_files(persona_id: str = "mike") -> int:
    """Index all supported files in the persona's files directory into memory."""
    from memory import get_memory_manager

    base = _resolve_base()
    if not base.exists():
        logger.warning("Files directory not found: %s", base)
        return 0

    mgr = get_memory_manager()
    count = 0
    for path in _iter_files(base=base):
        summary_payload = _build_summary_payload(path)
        content = "\n".join(summary_payload["summary"])
        mgr.index_file(path=str(path), content=content)
        count += 1
        logger.info("Indexed file: %s", path.name)

    logger.info("File indexing complete: %d files", count)
    return count
