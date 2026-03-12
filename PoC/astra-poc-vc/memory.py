"""
Memory Manager — Qdrant-backed persistent memory with domain-aware retrieval.

Designed as a standalone service so it can be extracted into a separate
memory agent without changing the interface.

Collections:
  - memories  : facts, episodes, reminders, workflow patterns
  - file_index: indexed summaries of user files
"""

from __future__ import annotations

import os
import json
import math
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("astra.memory")

# ---------------------------------------------------------------------------
# Optional Qdrant import — graceful degradation if not available
# ---------------------------------------------------------------------------
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchAny, MatchValue,
        ScoredPoint,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed — memory will use in-process fallback")

# ---------------------------------------------------------------------------
# In-process fallback (no Qdrant) — good enough for unit tests
# ---------------------------------------------------------------------------

class _InMemoryStore:
    """Simple list-based fallback when Qdrant is unavailable."""

    def __init__(self):
        self._memories: list[dict] = []
        self._files: list[dict] = []

    def upsert_memory(self, point: dict):
        self._memories = [m for m in self._memories if m["id"] != point["id"]]
        self._memories.append(point)

    def search_memories(self, domains: list[str], memory_type: Optional[str],
                        limit: int) -> list[dict]:
        results = []
        for m in self._memories:
            payload = m.get("payload", {})
            if domains and not any(d in payload.get("domains", []) for d in domains):
                continue
            if memory_type and payload.get("type") != memory_type:
                continue
            results.append(m)
        # Sort by created_at descending
        results.sort(key=lambda x: x["payload"].get("created_at", ""), reverse=True)
        return results[:limit]

    def upsert_file(self, point: dict):
        self._files = [f for f in self._files if f["id"] != point["id"]]
        self._files.append(point)

    def search_files(self, domains: list[str], limit: int) -> list[dict]:
        results = []
        for f in self._files:
            payload = f.get("payload", {})
            if domains and not any(d in payload.get("domains", []) for d in domains):
                continue
            results.append(f)
        return results[:limit]

    def get_all_files(self) -> list[dict]:
        return list(self._files)


# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------

MEMORY_TYPES = ("fact", "episode", "reminder", "workflow", "file_summary")
VECTOR_SIZE = 1536  # text-embedding-3-small


class MemoryManager:
    """
    Stores and retrieves memories with domain-aware filtering.

    Can be used directly by the agent or wrapped as a separate service.
    Falls back to in-process store if Qdrant is unavailable.
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        persona_id: str = "mike",
        openai_api_key: Optional[str] = None,
    ):
        self.persona_id = persona_id
        self._store = None
        self._embedder = None

        # Try Qdrant
        if QDRANT_AVAILABLE:
            try:
                self._qdrant = QdrantClient(url=qdrant_url, timeout=3)
                self._qdrant.get_collections()  # connectivity check
                self._ensure_collections()
                logger.info("MemoryManager connected to Qdrant at %s", qdrant_url)
            except Exception as e:
                logger.warning("Qdrant unavailable (%s) — using in-process fallback", e)
                self._qdrant = None
                self._store = _InMemoryStore()
        else:
            self._qdrant = None
            self._store = _InMemoryStore()

        # Try OpenAI embeddings
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self._embedder = OpenAI(api_key=api_key)
                logger.info("MemoryManager using OpenAI embeddings")
            except ImportError:
                logger.warning("openai package not installed — embeddings disabled")

    def _ensure_collections(self):
        """Create Qdrant collections if they don't exist."""
        existing = {c.name for c in self._qdrant.get_collections().collections}
        for name in ("memories", "file_index"):
            if name not in existing:
                self._qdrant.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection: %s", name)

    def _embed(self, text: str) -> list[float]:
        """Embed text. Returns zero vector if embedder unavailable."""
        if self._embedder:
            try:
                resp = self._embedder.embeddings.create(
                    model="text-embedding-3-small",
                    input=text[:8000],
                )
                return resp.data[0].embedding
            except Exception as e:
                logger.warning("Embedding failed: %s", e)
        # Fallback: deterministic pseudo-vector from hash (for testing)
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vec = []
        for i in range(VECTOR_SIZE):
            vec.append(((h >> (i % 64)) & 0xFF) / 255.0 - 0.5)
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        memory_type: str = "fact",
        tags: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
    ) -> str:
        """Store a memory. Returns the memory ID."""
        if memory_type not in MEMORY_TYPES:
            memory_type = "fact"

        # Auto-classify domain if not provided
        if not domains:
            from domain_router import classify
            domains = classify(content).domains

        point_id = str(uuid.uuid4())
        payload = {
            "persona_id": self.persona_id,
            "type": memory_type,
            "domains": domains,
            "content": content,
            "tags": tags or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "access_count": 0,
        }
        vector = self._embed(content)

        if self._qdrant:
            self._qdrant.upsert(
                collection_name="memories",
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
        else:
            self._store.upsert_memory({"id": point_id, "payload": payload, "vector": vector})

        logger.debug("Stored memory [%s] domains=%s: %s", memory_type, domains, content[:80])
        return point_id

    def retrieve(
        self,
        query: str,
        domains: Optional[list[str]] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Retrieve relevant memories, filtered by domain.
        Returns list of payload dicts, ranked by relevance + recency.
        """
        if self._qdrant:
            return self._retrieve_qdrant(query, domains, memory_type, limit)
        return self._retrieve_fallback(query, domains, memory_type, limit)

    def _retrieve_qdrant(self, query, domains, memory_type, limit) -> list[dict]:
        vector = self._embed(query)
        conditions = [
            FieldCondition(key="persona_id", match=MatchValue(value=self.persona_id))
        ]
        if domains:
            conditions.append(
                FieldCondition(key="domains", match=MatchAny(any=domains))
            )
        if memory_type:
            conditions.append(
                FieldCondition(key="type", match=MatchValue(value=memory_type))
            )

        results = self._qdrant.search(
            collection_name="memories",
            query_vector=vector,
            query_filter=Filter(must=conditions),
            limit=limit,
            with_payload=True,
        )
        return [r.payload for r in results]

    def _retrieve_fallback(self, query, domains, memory_type, limit) -> list[dict]:
        return [
            m["payload"]
            for m in self._store.search_memories(domains or [], memory_type, limit)
        ]

    def index_file(
        self,
        path: str,
        content: str,
        domains: Optional[list[str]] = None,
    ) -> str:
        """Index a file into the file_index collection."""
        filename = Path(path).name
        summary = content[:600]  # first 600 chars as summary

        if not domains:
            from domain_router import classify
            domains = classify(f"{filename} {summary}").domains

        point_id = str(uuid.uuid4())
        payload = {
            "persona_id": self.persona_id,
            "filename": filename,
            "path": path,
            "domains": domains,
            "summary": summary,
            "file_type": Path(path).suffix.lstrip("."),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        vector = self._embed(f"{filename}\n{summary}")

        if self._qdrant:
            self._qdrant.upsert(
                collection_name="file_index",
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
        else:
            self._store.upsert_file({"id": point_id, "payload": payload, "vector": vector})

        logger.debug("Indexed file: %s domains=%s", filename, domains)
        return point_id

    def search_files(
        self,
        query: str,
        domains: Optional[list[str]] = None,
        limit: int = 3,
    ) -> list[dict]:
        """Search indexed files by semantic similarity, filtered by domain."""
        if self._qdrant:
            return self._search_files_qdrant(query, domains, limit)
        return self._search_files_fallback(domains, limit)

    def _search_files_qdrant(self, query, domains, limit) -> list[dict]:
        vector = self._embed(query)
        conditions = [
            FieldCondition(key="persona_id", match=MatchValue(value=self.persona_id))
        ]
        if domains:
            conditions.append(
                FieldCondition(key="domains", match=MatchAny(any=domains))
            )
        results = self._qdrant.search(
            collection_name="file_index",
            query_vector=vector,
            query_filter=Filter(must=conditions),
            limit=limit,
            with_payload=True,
        )
        return [r.payload for r in results]

    def _search_files_fallback(self, domains, limit) -> list[dict]:
        return [
            f["payload"]
            for f in self._store.search_files(domains or [], limit)
        ]

    def list_all_files(self) -> list[dict]:
        """List all indexed files."""
        if self._qdrant:
            results = self._qdrant.scroll(
                collection_name="file_index",
                scroll_filter=Filter(must=[
                    FieldCondition(key="persona_id", match=MatchValue(value=self.persona_id))
                ]),
                limit=100,
                with_payload=True,
            )
            return [r.payload for r in results[0]]
        return [f["payload"] for f in self._store.get_all_files()]

    def format_for_prompt(self, memories: list[dict], files: list[dict]) -> str:
        """Format retrieved context for injection into the system prompt."""
        parts = []
        if memories:
            parts.append("### Relevant Memory:")
            for m in memories:
                mtype = m.get("type", "fact")
                content = m.get("content", "")
                parts.append(f"- [{mtype}] {content}")
        if files:
            parts.append("### Relevant Files:")
            for f in files:
                fname = f.get("filename", "")
                summary = f.get("summary", "")[:120]
                domains = ", ".join(f.get("domains", []))
                parts.append(f"- {fname} ({domains}): {summary}…")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            persona_id="mike",
        )
    return _manager
