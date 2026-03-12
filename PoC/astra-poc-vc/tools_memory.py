"""
Memory tools — exposed to the agent for explicit memory operations.
The agent can store facts, search memory, and manage workflows.
"""

from __future__ import annotations

import json
from typing import Optional
from langchain_core.tools import tool


@tool
def store_memory(content: str, memory_type: str = "fact", tags: str = "") -> str:
    """Store a memory or note for future reference.
    memory_type: 'fact' (preference/info), 'episode' (what happened), 'reminder' (time-sensitive)
    tags: comma-separated tags (optional)
    Example: store_memory('Mike prefers morning meetings', 'fact', 'scheduling')"""
    from memory import get_memory_manager
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    mgr = get_memory_manager()
    mem_id = mgr.store(content, memory_type=memory_type, tags=tag_list)
    return f"Stored [{memory_type}]: {content[:80]}… (id: {mem_id[:8]})"


@tool
def search_memory(query: str, memory_type: Optional[str] = None) -> str:
    """Search stored memories relevant to a query.
    Optionally filter by type: 'fact', 'episode', 'reminder'.
    Returns the most relevant memories for the given topic."""
    from memory import get_memory_manager
    from domain_router import classify
    domains = classify(query).domains
    mgr = get_memory_manager()
    results = mgr.retrieve(query, domains=domains, memory_type=memory_type, limit=5)
    if not results:
        return json.dumps({"message": "No relevant memories found.", "results": []})
    return json.dumps({
        "query": query,
        "domains": domains,
        "results": [
            {"type": r.get("type"), "content": r.get("content"), "tags": r.get("tags", [])}
            for r in results
        ],
    }, indent=2)


memory_tools = [store_memory, search_memory]
