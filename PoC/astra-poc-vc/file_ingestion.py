"""Cached ingestion helpers for Astra file summaries.

This module normalizes supported files into either:
- text mode: markdown and PDF documents
- image mode: image assets

The ingestion path is deterministic by default so previews/search work offline.
If FILE_INGESTION_USE_LLM=1 and OpenAI credentials are configured, the module
will attempt to enhance summaries with the configured chat model and fall back
silently on local heuristics when that fails.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("astra.file_ingestion")

_META_FILENAME = ".astra_meta.json"
_CACHE_VERSION = 1
_MAX_SEARCH_TEXT_CHARS = 4000
_MAX_CONTENT_PREVIEW_CHARS = 4000

TEXT_EXTENSIONS = {".md"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}

_STOP_WORDS = {
    "a", "about", "after", "all", "an", "and", "are", "as", "at", "be", "by",
    "for", "from", "how", "in", "into", "is", "it", "its", "of", "on", "or",
    "our", "that", "the", "their", "them", "they", "this", "to", "was", "we",
    "with", "you", "your",
}


def _read_sidecar(path: Path) -> dict[str, Any]:
    meta_file = path.parent / _META_FILENAME
    if not meta_file.exists():
        return {}
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_ingestion_meta(path: Path) -> dict[str, Any]:
    return _read_sidecar(path).get(path.name, {})


def _save_ingestion_meta(path: Path, data: dict[str, Any]) -> None:
    meta_file = path.parent / _META_FILENAME
    all_meta = _read_sidecar(path)
    current = dict(all_meta.get(path.name, {}))
    current.update(data)
    all_meta[path.name] = current
    try:
        meta_file.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Failed to persist ingestion metadata for %s", path, exc_info=True)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _readable_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _filename_keywords(path: Path) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", _readable_name(path).lower())
    seen: list[str] = []
    for token in tokens:
        if token in _STOP_WORDS or len(token) < 2 or token in seen:
            continue
        seen.append(token)
    return seen[:8]


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _text_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _extract_headings(text: str) -> list[str]:
    headings = []
    for line in _text_lines(text):
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())
    return headings[:5]


def _top_keywords(text: str, *, extra: list[str] | None = None) -> list[str]:
    counts: dict[str, int] = {}
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if len(token) < 3 or token in _STOP_WORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    keywords = [token for token, _ in ranked[:8]]
    for token in extra or []:
        if token not in keywords:
            keywords.append(token)
    return keywords[:8]


def _fallback_text_summary(text: str, path: Path, source_type: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    headings = _extract_headings(normalized)
    sentences = _text_sentences(normalized)
    lines = _text_lines(normalized)

    summary_short = ""
    if headings:
        summary_short = headings[0]
    elif sentences:
        summary_short = sentences[0][:220]
    else:
        summary_short = f"{source_type.upper()} file: {_readable_name(path)}"

    bullets: list[str] = []
    if headings:
        bullets.append(f"Primary heading: {headings[0]}")
    if len(headings) > 1:
        bullets.append(f"Additional sections: {', '.join(headings[1:3])}")
    elif sentences:
        bullets.append(sentences[0][:220])
    for line in lines:
        plain = line.lstrip("#").strip()
        if plain and plain not in bullets and len(plain) > 20:
            bullets.append(plain[:220])
        if len(bullets) >= 3:
            break
    if not bullets:
        bullets = [f"{source_type.upper()} file available for review."]

    keywords = _top_keywords(normalized, extra=_filename_keywords(path))
    preview = normalized[:_MAX_CONTENT_PREVIEW_CHARS]
    search_text = " ".join(
        part for part in [
            path.name,
            summary_short,
            " ".join(bullets),
            " ".join(keywords),
            normalized[:3000],
        ]
        if part
    )[:_MAX_SEARCH_TEXT_CHARS]

    return {
        "mode": "text",
        "source_type": source_type,
        "summary_short": summary_short,
        "summary_bullets": bullets[:3],
        "keywords": keywords,
        "search_text": search_text,
        "content_preview": preview,
        "text_truncated": len(normalized) > _MAX_CONTENT_PREVIEW_CHARS,
        "text_length": len(normalized),
        "raw_text_excerpt": normalized[:3000],
        "needs_ocr": False,
    }


def _llm_enabled() -> bool:
    return os.getenv("FILE_INGESTION_USE_LLM", "0") == "1" and bool(os.getenv("OPENAI_API_KEY"))


def _try_llm_text_summary(text: str, path: Path, source_type: str) -> dict[str, Any] | None:
    if not _llm_enabled():
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None

    llm = ChatOpenAI(
        model=os.getenv("FILE_INGESTION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    prompt_text = text[:8000]
    try:
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Return strict JSON with keys summary_short, summary_bullets, keywords. "
                        "summary_bullets must be an array of 2 or 3 short strings. "
                        "keywords must be an array of up to 8 strings."
                    )
                ),
                HumanMessage(
                    content=(
                        f"File: {path.name}\n"
                        f"Source type: {source_type}\n"
                        f"Text:\n{prompt_text}"
                    )
                ),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        payload = json.loads(str(content).strip())
        summary_short = str(payload.get("summary_short", "")).strip()
        bullets = [str(item).strip() for item in payload.get("summary_bullets", []) if str(item).strip()]
        keywords = [str(item).strip().lower() for item in payload.get("keywords", []) if str(item).strip()]
        if not summary_short or not bullets:
            return None
        return {
            "mode": "text",
            "source_type": source_type,
            "summary_short": summary_short,
            "summary_bullets": bullets[:3],
            "keywords": keywords[:8],
            "search_text": " ".join([path.name, summary_short, " ".join(bullets), " ".join(keywords), text[:3000]])[
                :_MAX_SEARCH_TEXT_CHARS
            ],
            "content_preview": _normalize_text(text)[:_MAX_CONTENT_PREVIEW_CHARS],
            "text_truncated": len(_normalize_text(text)) > _MAX_CONTENT_PREVIEW_CHARS,
            "text_length": len(text),
            "raw_text_excerpt": _normalize_text(text)[:3000],
            "needs_ocr": False,
        }
    except Exception:
        logger.debug("LLM text summarization failed for %s", path, exc_info=True)
        return None


def _extract_pdf_text(path: Path) -> str:
    reader_module = None
    reader_class = None
    for module_name, class_name in (("pypdf", "PdfReader"), ("PyPDF2", "PdfReader")):
        try:
            reader_module = __import__(module_name, fromlist=[class_name])
            reader_class = getattr(reader_module, class_name)
            break
        except Exception:
            continue
    if reader_class is None:
        return ""

    try:
        reader = reader_class(str(path))
        pages = []
        for index, page in enumerate(getattr(reader, "pages", []), start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(f"[Page {index}]\n{page_text}")
        return "\n\n".join(pages).strip()
    except Exception:
        logger.debug("PDF extraction failed for %s", path, exc_info=True)
        return ""


def _guess_image_classification(path: Path, tokens: list[str]) -> str:
    joined = " ".join(tokens)
    if any(term in joined for term in ("chart", "heatmap", "graph", "plot", "dashboard")):
        return "chart"
    if any(term in joined for term in ("mock", "mockup", "ui", "screen", "screenshot")):
        return "mockup"
    if any(term in joined for term in ("scan", "receipt", "invoice", "document")):
        return "document"
    if any(term in joined for term in ("photo", "image", "picture")):
        return "photo"
    return "image"


def _try_llm_image_summary(path: Path) -> dict[str, Any] | None:
    if not _llm_enabled():
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None

    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }.get(path.suffix.lower(), "application/octet-stream")
    try:
        data_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        llm = ChatOpenAI(
            model=os.getenv("FILE_INGESTION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Return strict JSON with keys description, tags, visible_text, classification. "
                        "tags must be an array of short strings."
                    )
                ),
                HumanMessage(
                    content=[
                        {"type": "text", "text": f"Analyze image file {path.name}."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                ),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        payload = json.loads(str(content).strip())
        description = str(payload.get("description", "")).strip()
        tags = [str(item).strip().lower() for item in payload.get("tags", []) if str(item).strip()]
        visible_text = str(payload.get("visible_text", "")).strip()
        classification = str(payload.get("classification", "image")).strip() or "image"
        if not description:
            return None
        search_text = " ".join([path.name, description, visible_text, " ".join(tags)])[:_MAX_SEARCH_TEXT_CHARS]
        return {
            "mode": "image",
            "source_type": "image",
            "summary_short": description,
            "summary_bullets": [
                description,
                f"Classification: {classification}",
            ],
            "keywords": tags[:8],
            "search_text": search_text,
            "description": description,
            "ocr_text": visible_text,
            "classification": classification,
            "needs_ocr": False,
        }
    except Exception:
        logger.debug("LLM image analysis failed for %s", path, exc_info=True)
        return None


def _ingest_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    summary = _try_llm_text_summary(text, path, "md") or _fallback_text_summary(text, path, "md")
    summary["analysis_ready"] = True
    return summary


def _ingest_pdf(path: Path) -> dict[str, Any]:
    text = _extract_pdf_text(path)
    if text:
        summary = _try_llm_text_summary(text, path, "pdf") or _fallback_text_summary(text, path, "pdf")
        summary["analysis_ready"] = True
        return summary

    readable_name = _readable_name(path)
    keywords = _filename_keywords(path)
    return {
        "mode": "text",
        "source_type": "pdf",
        "summary_short": f"PDF file available: {readable_name}",
        "summary_bullets": [
            f"PDF file: {path.name}",
            "Text extraction produced no usable text.",
            "Marking this file for OCR or vision fallback.",
        ],
        "keywords": ["pdf", *keywords][:8],
        "search_text": " ".join([path.name, readable_name, "pdf", *keywords])[:_MAX_SEARCH_TEXT_CHARS],
        "content_preview": "",
        "text_truncated": False,
        "text_length": 0,
        "raw_text_excerpt": "",
        "needs_ocr": True,
        "analysis_ready": False,
    }


def _ingest_image(path: Path) -> dict[str, Any]:
    llm_result = _try_llm_image_summary(path)
    if llm_result is not None:
        llm_result["analysis_ready"] = True
        return llm_result

    tokens = _filename_keywords(path)
    classification = _guess_image_classification(path, tokens)
    readable_name = _readable_name(path)
    description = f"Image asset: {readable_name}"
    search_text = " ".join([path.name, description, classification, " ".join(tokens)])[:_MAX_SEARCH_TEXT_CHARS]
    return {
        "mode": "image",
        "source_type": "image",
        "summary_short": description,
        "summary_bullets": [
            description,
            f"Likely {classification} content based on filename metadata.",
            "Open the image preview for full visual inspection.",
        ],
        "keywords": tokens[:8],
        "search_text": search_text,
        "description": description,
        "ocr_text": "",
        "classification": classification,
        "needs_ocr": False,
        "analysis_ready": False,
    }


def ingest_file(path: Path) -> dict[str, Any]:
    """Return cached normalized ingestion data for a supported file."""
    suffix = path.suffix.lower()
    if suffix not in TEXT_EXTENSIONS | PDF_EXTENSIONS | IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    content_hash = _hash_file(path)
    cached = _load_ingestion_meta(path)
    if (
        cached.get("content_hash") == content_hash
        and cached.get("cache_version") == _CACHE_VERSION
        and cached.get("mode") in {"text", "image"}
    ):
        return cached

    if suffix in TEXT_EXTENSIONS:
        payload = _ingest_markdown(path)
    elif suffix in PDF_EXTENSIONS:
        payload = _ingest_pdf(path)
    else:
        payload = _ingest_image(path)

    payload.update(
        {
            "content_hash": content_hash,
            "cache_version": _CACHE_VERSION,
            "ingested_at": _now_iso(),
        }
    )
    _save_ingestion_meta(path, payload)
    return payload
