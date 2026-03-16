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


# ---------------------------------------------------------------------------
# Workflow tools — list, enable, disable automated workflows
# ---------------------------------------------------------------------------

@tool
def list_workflows() -> str:
    """List all available workflows with their current status.
    Returns workflow id, name, description, and enabled/disabled state."""
    from workflow_engine import get_workflow_engine
    engine = get_workflow_engine()
    workflows = engine.list_workflows()
    return json.dumps({
        "workflows": [
            {
                "id": w["id"],
                "name": w["name"],
                "description": w["description"],
                "enabled": w["enabled"],
                "trigger": w.get("trigger", ""),
            }
            for w in workflows
        ],
        "count": len(workflows),
    }, indent=2)


@tool
def enable_workflow(workflow_id: str) -> str:
    """Enable an automated workflow by its ID.
    Once enabled, the workflow will run automatically when its trigger conditions are met.
    Use list_workflows() first to see available workflow IDs."""
    from workflow_engine import get_workflow_engine
    engine = get_workflow_engine()
    workflows = engine.list_workflows()
    wf = next((w for w in workflows if w["id"] == workflow_id), None)
    if not wf:
        return json.dumps({"success": False, "error": f"Workflow '{workflow_id}' not found"})
    if wf["enabled"]:
        return json.dumps({"success": True, "message": f"Workflow '{wf['name']}' is already enabled"})
    engine.enable(workflow_id)
    return json.dumps({
        "success": True,
        "message": f"Workflow '{wf['name']}' is now enabled",
        "workflow": {"id": workflow_id, "name": wf["name"], "enabled": True},
    })


@tool
def disable_workflow(workflow_id: str) -> str:
    """Disable an automated workflow by its ID.
    The workflow will stop running automatically until re-enabled.
    Use list_workflows() first to see available workflow IDs."""
    from workflow_engine import get_workflow_engine
    engine = get_workflow_engine()
    workflows = engine.list_workflows()
    wf = next((w for w in workflows if w["id"] == workflow_id), None)
    if not wf:
        return json.dumps({"success": False, "error": f"Workflow '{workflow_id}' not found"})
    if not wf["enabled"]:
        return json.dumps({"success": True, "message": f"Workflow '{wf['name']}' is already disabled"})
    engine.disable(workflow_id)
    return json.dumps({
        "success": True,
        "message": f"Workflow '{wf['name']}' is now disabled",
        "workflow": {"id": workflow_id, "name": wf["name"], "enabled": False},
    })


memory_tools = [store_memory, search_memory, list_workflows, enable_workflow, disable_workflow]
