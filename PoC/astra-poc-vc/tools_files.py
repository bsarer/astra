"""
File system tools — lets the agent list, read, and search user files.
Files live in data/personas/mike/files/ (mounted into Docker at /app/data/personas/mike/files/).
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("astra.files")

SUPPORTED_EXTENSIONS = {".md", ".txt", ".json"}


def _resolve_base() -> Path:
    """Find the files directory, checking multiple locations."""
    env_override = os.getenv("PERSONA_FILES_DIR", "")
    candidates = [
        Path(env_override) if env_override else None,
        Path(__file__).parent / "data/personas/mike/files",
        Path("/app/data/personas/mike/files"),
        Path("data/personas/mike/files"),
    ]
    for p in candidates:
        if p is not None and p.exists() and p.is_dir():
            return p
    # Return best guess (next to this file) even if it doesn't exist yet
    return Path(__file__).parent / "data/personas/mike/files"


def _read_file_content(path: Path) -> str:
    """Read file content. Supports text/markdown. Returns empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Could not read %s: %s", path, e)
        return ""


@tool
def list_user_files(subdirectory: str = "") -> str:
    """List files available in Mike's personal file system.
    Returns filenames, types, and domain tags.
    Use this to discover what documents are available before reading them."""
    base = _resolve_base()
    target = base / subdirectory if subdirectory else base

    if not target.exists():
        return json.dumps({"error": f"Directory not found: {target}", "files": []})

    files = []
    for p in sorted(target.iterdir()):
        if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
            from domain_router import classify
            content_preview = _read_file_content(p)[:300]
            domains = classify(f"{p.name} {content_preview}").domains
            files.append({
                "filename": p.name,
                "path": str(p.relative_to(base)),
                "type": p.suffix.lstrip("."),
                "size_kb": round(p.stat().st_size / 1024, 1),
                "domains": domains,
            })

    return json.dumps({"files": files, "count": len(files)}, indent=2)


@tool
def read_user_file(filename: str) -> str:
    """Read the full content of a file from Mike's file system.
    Pass the filename (e.g. 'Acme_Pricing_Tiers.md') or relative path.
    Returns the file content as text."""
    base = _resolve_base()

    # Try direct filename match first, then path match
    candidates = [
        base / filename,
        base / Path(filename).name,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            content = _read_file_content(p)
            if content:
                return f"# {p.name}\n\n{content}"
            return f"Error: Could not read {p.name}"

    # Fuzzy match — find file containing the search term
    search = Path(filename).stem.lower()
    for p in base.rglob("*"):
        if p.is_file() and search in p.stem.lower():
            content = _read_file_content(p)
            if content:
                return f"# {p.name}\n\n{content}"

    return f"File not found: {filename}. Use list_user_files() to see available files."


@tool
def search_user_files(query: str) -> str:
    """Search Mike's files by topic or keyword.
    Uses domain-aware semantic search — returns the most relevant files for the query.
    Returns file summaries with relevance context."""
    from memory import get_memory_manager
    from domain_router import classify

    domains = classify(query).domains
    mgr = get_memory_manager()

    # Search indexed files
    results = mgr.search_files(query, domains=domains, limit=3)

    if not results:
        # Fallback: keyword scan across all files (split query into words)
        base = _resolve_base()
        results = []
        query_words = [w for w in query.lower().split() if len(w) > 2]
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
                content = _read_file_content(p)
                text = (p.name + " " + content).lower()
                if any(w in text for w in query_words):
                    from domain_router import classify as _classify
                    file_domains = _classify(f"{p.name} {content[:300]}").domains
                    # Only return if domain matches
                    if not domains or any(d in file_domains for d in domains):
                        results.append({
                            "filename": p.name,
                            "domains": file_domains,
                            "summary": content[:200],
                        })
        if not results:
            return json.dumps({"message": f"No files found matching '{query}'", "results": []})

    return json.dumps({
        "query": query,
        "domains_searched": domains,
        "results": [
            {
                "filename": r.get("filename"),
                "domains": r.get("domains", []),
                "summary": r.get("summary", "")[:200],
            }
            for r in results
        ],
    }, indent=2)


# All file tools for easy import
file_tools = [list_user_files, read_user_file, search_user_files]


# ---------------------------------------------------------------------------
# File indexing — called at startup
# ---------------------------------------------------------------------------

def index_all_files(persona_id: str = "mike") -> int:
    """Index all files in the persona's files directory into memory.
    Returns the number of files indexed."""
    from memory import get_memory_manager

    base = _resolve_base()
    if not base.exists():
        logger.warning("Files directory not found: %s", base)
        return 0

    mgr = get_memory_manager()
    count = 0
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
            content = _read_file_content(p)
            if content:
                mgr.index_file(
                    path=str(p),
                    content=content,
                )
                count += 1
                logger.info("Indexed file: %s", p.name)

    logger.info("File indexing complete: %d files", count)
    return count
