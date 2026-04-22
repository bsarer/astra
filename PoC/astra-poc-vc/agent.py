import os
import json
import logging
import re
import datetime
from typing import Literal, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from copilotkit.langgraph import CopilotKitState, copilotkit_customize_config, copilotkit_emit_state

from tracing import log_generation
load_dotenv()
logger = logging.getLogger("astra.agent")

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def load_prompt(name: str) -> str:
    with open(os.path.join(PROMPTS_DIR, f"{name}.md"), "r", encoding="utf-8") as f:
        return f.read().strip()

# Load prompts once at startup
# Lean base: system rules + persona only
BASE_SYSTEM = load_prompt("system") + "\n\n" + load_prompt("persona_context")
# UI catalog injected only when rendering is needed
UI_CATALOG = load_prompt("a2ui_catalog")

DEFAULT_MAX_INPUT_TOKENS = int(
    os.getenv("OPENAI_MAX_INPUT_TOKENS", os.getenv("MODEL_MAX_INPUT_TOKENS", "12000"))
)
DEFAULT_RESPONSE_TOKEN_RESERVE = int(os.getenv("OPENAI_RESPONSE_TOKEN_RESERVE", "1500"))
DEFAULT_MESSAGE_CHAR_LIMIT = int(os.getenv("OPENAI_MESSAGE_CHAR_LIMIT", "2400"))
DEFAULT_TOOL_CHAR_LIMIT = int(os.getenv("OPENAI_TOOL_CHAR_LIMIT", "1400"))
DEFAULT_LAST_HUMAN_CHAR_LIMIT = int(os.getenv("OPENAI_LAST_HUMAN_CHAR_LIMIT", "4000"))

# Canvas state: surface_id -> summary
_canvas_state: dict[str, dict] = {}
_processed_email_ids: set[str] = set()

# Tools that return data and MUST be followed by emit_ui
DATA_TOOLS = {
    "list_user_files", "open_user_file", "search_user_files",
    "create_markdown_document", "create_pdf_document", "merge_markdown_files", "merge_pdf_files",
    "create_user_folder", "rename_user_file", "move_user_file", "move_multiple_files", "move_files_in_folder", "categorize_user_files", "delete_user_file", "delete_multiple_files",
    "list_emails", "get_email", "search_emails",
    "list_calendar_events", "get_calendar_event",
    "get_stock_quote", "get_watchlist_summary", "get_stock_history", "analyze_stock_email_context",
    "get_upcoming_trip", "get_weather", "get_currency_exchange",
}


def get_canvas_context() -> str:
    surfaces = {k: v for k, v in _canvas_state.items() if not k.startswith("_")}
    if not surfaces:
        ctx = "Canvas is EMPTY — no widgets are visible. You MUST call emit_ui for any visual request."
    else:
        lines = ["Visible surfaces (if a surface is NOT here, it was CLOSED — re-create it when asked):"]
        for sid, info in surfaces.items():
            lines.append(f"  - {sid}: {info.get('summary', 'unknown')}")
        ctx = "\n".join(lines)
    return ctx


def get_processed_emails_context() -> str:
    if not _processed_email_ids:
        return ""
    return f"Already processed email IDs (skip these): {', '.join(sorted(_processed_email_ids))}"


class GraphState(CopilotKitState):
    ui_event: dict | None
    needs_ui: bool


# ── Built-in tools ──────────────────────────────────────────────────────────

@tool
def install_python_packages(package_names: List[str]) -> str:
    """Install Python packages via pip. Use before run_python_code if a library is missing."""
    import subprocess, sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + package_names)
        return f"Installed: {', '.join(package_names)}"
    except subprocess.CalledProcessError as e:
        return f"Install failed: {e}"


@tool
def render_widget(id: str, html: str, width_percent: int, height_px: int) -> str:
    """Legacy HTML widget renderer. Prefer emit_ui for new widgets."""
    return f"Widget {id} rendered."


@tool
def run_python_code(code: str) -> str:
    """Execute Python code in an isolated environment. Use print() for output."""
    import sys
    from io import StringIO
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    def _run(code):
        old = sys.stdout
        buf = sys.stdout = StringIO()
        env = {}
        try:
            exec(code, {}, env)
            out = buf.getvalue()
            if not out and "result" in env:
                out = str(env["result"])
        except Exception as e:
            out = f"Error: {e}"
        finally:
            sys.stdout = old
        return out

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_run, code).result(timeout=30)
    except FuturesTimeout:
        return "Error: timed out after 30s"
    except Exception as e:
        return f"Error: {e}"


@tool
def emit_ui(surface_id: str, components: list[dict], grid: dict | None = None) -> str:
    """Render a declarative UI surface on the user's dashboard.

    surface_id: unique name for this window (e.g. 'my-files', 'stock-alert')
    components: flat adjacency list of A2UI components
    grid: optional size hint {"w": 1-12, "h": row units}

    Available component types: Text, Button, Card, Row, Column, Divider, Tabs,
    Image, Icon, List, StockTicker, StockAlert, EmailRow, MetricCard,
    SparklineChart, CalendarEvent, Clock, FileExplorer
    """
    comp_types = [c.get("type", "?") for c in components[:5]]
    summary = f"{len(components)} components ({', '.join(comp_types)})"
    _canvas_state[surface_id] = {
        "summary": summary,
        "component_count": len(components),
        "surface_id": surface_id,
        "components": components,
        "grid": grid,
    }
    return json.dumps({
        "status": "rendered",
        "surface_id": surface_id,
        "component_count": len(components),
        "canvas_size": len(_canvas_state),
    })


# ── Import domain tools ──────────────────────────────────────────────────────

from tools_email_calendar import email_calendar_tools
from tools_travel import travel_tools
from tools_stock import stock_tools
from tools_files import file_tools
from tools_memory import memory_tools
from workflow_engine import get_workflow_engine

tools = (
    [run_python_code, install_python_packages, render_widget, emit_ui]
    + email_calendar_tools + travel_tools + stock_tools + file_tools + memory_tools
)
_builtin_tool_node = ToolNode(tools)

# ── LLM setup ────────────────────────────────────────────────────────────────

llm_model = os.getenv("OPENAI_MODEL", os.getenv("MODEL", "gpt-4o-mini"))
llm_kwargs = {"model": llm_model, "temperature": 0.3, "streaming": True}
if os.getenv("OPENAI_BASE_URL"):
    llm_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
if os.getenv("OPENAI_API_KEY"):
    llm_kwargs["api_key"] = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(**llm_kwargs)
llm_with_tools = llm.bind_tools(tools)


# ── Dashboard greeting (shown on initial connect) ────────────────────────────

def _build_dashboard_greeting() -> tuple[list[dict], str]:
    """Build the default dashboard components and greeting text."""
    hour = datetime.datetime.now().hour
    time_of_day = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    components = [
        {"id": "root", "type": "Column", "props": {"gap": "16px"}, "children": ["greeting", "stats-row", "actions"]},
        {"id": "greeting", "type": "Card", "props": {"variant": "glass"}, "children": ["greet-text", "greet-sub"]},
        {"id": "greet-text", "type": "Text", "props": {"text": f"Good {time_of_day}, Mike 👋", "variant": "title", "weight": "bold"}, "children": []},
        {"id": "greet-sub", "type": "Text", "props": {"text": "Vertex Solutions · Austin, TX", "variant": "muted"}, "children": []},
        {"id": "stats-row", "type": "Row", "props": {"gap": "12px", "wrap": True}, "children": ["m1", "m2", "m3"]},
        {"id": "m1", "type": "MetricCard", "props": {"label": "Q1 Target", "value": "$1.2M", "change": "87% attained", "color": "cyan"}, "children": []},
        {"id": "m2", "type": "MetricCard", "props": {"label": "Key Clients", "value": "3", "change": "Acme · BluePeak · NovaTech", "color": "blue"}, "children": []},
        {"id": "m3", "type": "MetricCard", "props": {"label": "Team", "value": "3 reps", "change": "Sarah · Jake · Priya", "color": "green"}, "children": []},
        {"id": "actions", "type": "Row", "props": {"gap": "8px", "wrap": True}, "children": ["b1", "b2", "b3", "b4"]},
        {"id": "b1", "type": "Button", "props": {"label": "📧 Inbox", "action": "show_inbox", "variant": "secondary"}, "children": []},
        {"id": "b2", "type": "Button", "props": {"label": "📅 Calendar", "action": "show_calendar", "variant": "secondary"}, "children": []},
        {"id": "b3", "type": "Button", "props": {"label": "📈 Stocks", "action": "show_stocks", "variant": "secondary"}, "children": []},
        {"id": "b4", "type": "Button", "props": {"label": "📁 Files", "action": "show_files", "variant": "secondary"}, "children": []},
    ]
    return components, time_of_day


def _sanitize_tool_calls(messages: list) -> list:
    """Remove AIMessage tool_calls that lack a matching ToolMessage response.

    OpenAI requires every tool_call_id in an assistant message to have a
    corresponding tool-role message.  If the graph was interrupted mid-turn
    (timeout, crash, etc.) the checkpointer may persist an orphaned tool call.
    This strips those to prevent 400 errors.
    """
    # Collect all tool_call_ids that have a ToolMessage response
    answered_ids: set[str] = set()
    for m in messages:
        # Check both ToolMessage type and role-based detection
        if isinstance(m, ToolMessage):
            answered_ids.add(getattr(m, "tool_call_id", ""))
        elif getattr(m, "type", None) == "tool" or getattr(m, "role", None) == "tool":
            answered_ids.add(getattr(m, "tool_call_id", ""))

    sanitized = []
    for m in messages:
        if isinstance(m, AIMessage) or (getattr(m, "type", None) == "ai") or (getattr(m, "role", None) == "assistant"):
            tc = getattr(m, "tool_calls", None) or []
            # Also check additional_kwargs for tool_calls (some LangChain versions)
            if not tc:
                tc = (getattr(m, "additional_kwargs", None) or {}).get("tool_calls", [])
            if tc:
                good_calls = [t for t in tc if (t.get("id") or t.get("tool_call_id", "")) in answered_ids]
                if good_calls:
                    try:
                        m = m.model_copy(update={"tool_calls": good_calls})
                    except Exception:
                        pass  # If model_copy fails, keep original
                    sanitized.append(m)
                elif getattr(m, "content", None):
                    # Has text content but orphaned tool_calls — strip them
                    try:
                        m = m.model_copy(update={"tool_calls": []})
                        # Also clear additional_kwargs tool_calls
                        ak = dict(getattr(m, "additional_kwargs", None) or {})
                        ak.pop("tool_calls", None)
                        m = m.model_copy(update={"additional_kwargs": ak})
                    except Exception:
                        pass
                    sanitized.append(m)
                else:
                    # Pure tool_call message with no responses — drop entirely
                    logger.debug("Dropping orphaned tool_call message: %s",
                                 [t.get("id", "?") for t in tc])
            else:
                sanitized.append(m)
        else:
            sanitized.append(m)
    return sanitized


def _stringify_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                parts.append(text if isinstance(text, str) and text else json.dumps(block, ensure_ascii=False))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def _truncate_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    if limit < 160:
        return text[:limit]

    marker = f"\n\n...[truncated {len(text) - limit} chars]...\n\n"
    remaining = limit - len(marker)
    head = max(32, int(remaining * 0.7))
    tail = max(16, remaining - head)
    return text[:head] + marker + text[-tail:]


def _estimate_tokens_for_text(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _estimate_message_tokens(message) -> int:
    text = _stringify_message_content(getattr(message, "content", ""))
    total = 6 + _estimate_tokens_for_text(text)

    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        total += _estimate_tokens_for_text(json.dumps(tool_calls, ensure_ascii=False))

    tool_call_id = getattr(message, "tool_call_id", "")
    if tool_call_id:
        total += _estimate_tokens_for_text(tool_call_id)

    additional_kwargs = getattr(message, "additional_kwargs", None) or {}
    if additional_kwargs:
        total += _estimate_tokens_for_text(json.dumps(additional_kwargs, ensure_ascii=False)[:600])

    return total


def _compact_message(message, *, char_limit: int):
    text = _stringify_message_content(getattr(message, "content", ""))
    truncated = _truncate_text(text, char_limit)
    if truncated == text:
        return message
    try:
        return message.model_copy(update={"content": truncated})
    except Exception:
        return message


def _build_history_units(messages: list) -> list[list]:
    units: list[list] = []
    current: list = []

    for message in messages:
        if isinstance(message, HumanMessage) and current:
            units.append(current)
            current = [message]
        else:
            current.append(message)

    if current:
        units.append(current)
    return units


def _trim_history_by_budget(
    messages: list,
    *,
    history_budget_tokens: int,
    message_char_limit: int,
    tool_char_limit: int,
    last_human_char_limit: int,
) -> list:
    if history_budget_tokens <= 0 or not messages:
        return []

    last_human_idx = None
    for idx in range(len(messages) - 1, -1, -1):
        if isinstance(messages[idx], HumanMessage):
            last_human_idx = idx
            break

    compacted = []
    for idx, message in enumerate(messages):
        if isinstance(message, ToolMessage):
            limit = tool_char_limit
        elif idx == last_human_idx and isinstance(message, HumanMessage):
            limit = last_human_char_limit
        else:
            limit = message_char_limit
        compacted.append(_compact_message(message, char_limit=limit))

    units = _build_history_units(compacted)
    if not units:
        return compacted

    kept_units: list[list] = []
    used_tokens = 0

    for unit in reversed(units):
        unit_tokens = sum(_estimate_message_tokens(message) for message in unit)
        if kept_units and used_tokens + unit_tokens > history_budget_tokens:
            break
        kept_units.append(unit)
        used_tokens += unit_tokens
        if used_tokens >= history_budget_tokens:
            break

    if not kept_units:
        kept_units = [units[-1]]

    trimmed = []
    for unit in reversed(kept_units):
        trimmed.extend(unit)
    return trimmed


def _build_canvas_reminder(canvas_ctx: str) -> SystemMessage:
    return SystemMessage(content=(
        f"[CANVAS STATE — AUTHORITATIVE, OVERRIDES YOUR MEMORY]\n{canvas_ctx}\n"
        "If the user asks for something NOT listed above, you MUST call emit_ui to create it. "
        "Do NOT say 'already displayed' unless the surface_id appears in the list above."
    ))


def _compose_prompt_messages(full_system: str, history: list, canvas_ctx: str) -> list:
    canvas_reminder = _build_canvas_reminder(canvas_ctx)

    last_human_idx = None
    for idx in range(len(history) - 1, -1, -1):
        if isinstance(history[idx], HumanMessage):
            last_human_idx = idx
            break

    if last_human_idx is not None and last_human_idx > 0:
        return (
            [SystemMessage(content=full_system)]
            + history[:last_human_idx]
            + [canvas_reminder]
            + history[last_human_idx:]
        )
    return [SystemMessage(content=full_system), canvas_reminder] + history


def _prepare_messages_for_model(
    full_system: str,
    canvas_ctx: str,
    messages: list,
    *,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    response_token_reserve: int = DEFAULT_RESPONSE_TOKEN_RESERVE,
    message_char_limit: int = DEFAULT_MESSAGE_CHAR_LIMIT,
    tool_char_limit: int = DEFAULT_TOOL_CHAR_LIMIT,
    last_human_char_limit: int = DEFAULT_LAST_HUMAN_CHAR_LIMIT,
) -> list:
    fixed_messages = [SystemMessage(content=full_system), _build_canvas_reminder(canvas_ctx)]
    fixed_tokens = sum(_estimate_message_tokens(message) for message in fixed_messages)
    history_budget = max(256, max_input_tokens - response_token_reserve - fixed_tokens)

    trimmed_history = _trim_history_by_budget(
        messages,
        history_budget_tokens=history_budget,
        message_char_limit=message_char_limit,
        tool_char_limit=tool_char_limit,
        last_human_char_limit=last_human_char_limit,
    )
    final_messages = _compose_prompt_messages(full_system, trimmed_history, canvas_ctx)

    if sum(_estimate_message_tokens(message) for message in final_messages) <= max_input_tokens - response_token_reserve:
        return final_messages

    latest_turn_only = _trim_history_by_budget(
        messages,
        history_budget_tokens=history_budget,
        message_char_limit=max(600, message_char_limit // 2),
        tool_char_limit=max(300, tool_char_limit // 2),
        last_human_char_limit=max(1200, last_human_char_limit // 2),
    )
    return _compose_prompt_messages(full_system, latest_turn_only, canvas_ctx)


def _is_context_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "prompt too long" in text or "max context length" in text or "context length" in text


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def chatbot_node(state: GraphState, config: RunnableConfig):
    messages = state["messages"]
    needs_ui = state.get("needs_ui", False)

    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
    )

    # ── Initial connection: CopilotKit sends messages=[] on first connect ──
    if not messages or not last_human:
        components, time_of_day = _build_dashboard_greeting()
        ui_event = {"surface_id": "mike-dashboard", "components": components, "grid": {"w": 7, "h": 6}}
        _canvas_state["mike-dashboard"] = {"summary": "dashboard", "component_count": len(components)}
        try:
            await copilotkit_emit_state(config, {"ui_event": ui_event})
        except Exception as e:
            logger.debug("copilotkit_emit_state failed: %s", e)
        greeting_msg = AIMessage(content=f"Good {time_of_day}, Mike! Your dashboard is ready.")
        return {"messages": [greeting_msg], "ui_event": ui_event, "needs_ui": False}

    # Workflow engine trigger detection
    trigger = "user_message"
    if isinstance(last_human, str) and last_human.startswith("[SYSTEM]"):
        trigger = "session_start"
        if "bloomberg" in last_human.lower():
            trigger = "email_bloomberg"
        elif "email" in last_human.lower():
            trigger = "email_new"
    engine = get_workflow_engine()
    engine.start_turn(trigger)

    # Build system prompt — lean base always, UI catalog only when rendering needed
    canvas_ctx = get_canvas_context()
    email_ctx = get_processed_emails_context()

    system_parts = [BASE_SYSTEM]

    if needs_ui:
        # Inject UI catalog only when we're about to render
        system_parts.append(UI_CATALOG)

    system_parts.append(f"\n### Canvas State:\n(injected separately as authoritative reminder)")
    if email_ctx:
        system_parts.append(f"\n### Processed Emails:\n{email_ctx}")

    # Domain-aware memory injection (non-blocking)
    try:
        if last_human and not (isinstance(last_human, str) and last_human.startswith("[SYSTEM]")):
            from domain_router import classify
            from memory import get_memory_manager
            domains = classify(last_human).domains
            mgr = get_memory_manager()
            memories = mgr.retrieve(last_human, domains=domains, limit=3)
            files = mgr.search_files(last_human, domains=domains, limit=2)
            mem_ctx = mgr.format_for_prompt(memories, files)
            if mem_ctx:
                system_parts.append(f"\n{mem_ctx}")
    except Exception:
        pass

    full_system = "\n\n".join(system_parts)
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]

    # Sanitize: strip orphaned tool_calls that have no matching ToolMessage.
    # This prevents OpenAI 400 errors when a previous turn was interrupted.
    logger.info("PRE-SANITIZE: %d messages", len(filtered))
    for i, m in enumerate(filtered):
        tc = getattr(m, 'tool_calls', None) or []
        ak_tc = (getattr(m, 'additional_kwargs', None) or {}).get('tool_calls', [])
        tc_ids = [t.get("id", "?") for t in tc] if tc else []
        tool_call_id = getattr(m, 'tool_call_id', None)
        logger.info("  [%d] type=%-15s tc_ids=%-40s tool_call_id=%s content=%s",
                     i, type(m).__name__, tc_ids or "",
                     tool_call_id or "",
                     repr((getattr(m, 'content', '') or '')[:80]))

    filtered = _sanitize_tool_calls(filtered)

    logger.info("POST-SANITIZE: %d messages", len(filtered))
    for i, m in enumerate(filtered):
        tc = getattr(m, 'tool_calls', None) or []
        tc_ids = [t.get("id", "?") for t in tc] if tc else []
        tool_call_id = getattr(m, 'tool_call_id', None)
        logger.info("  [%d] type=%-15s tc_ids=%-40s tool_call_id=%s",
                     i, type(m).__name__, tc_ids or "", tool_call_id or "")

    final_messages = _prepare_messages_for_model(full_system, canvas_ctx, filtered)
    estimated_prompt_tokens = sum(_estimate_message_tokens(message) for message in final_messages)
    logger.info("Prepared %d prompt messages (~%d tokens)", len(final_messages), estimated_prompt_tokens)

    # Merge CopilotKit frontend actions into tools for this invocation
    ck_actions = state.get("copilotkit", {}).get("actions", [])
    if ck_actions:
        from copilotkit.langgraph import copilotkit_messages_to_langchain
        from langchain_core.tools import StructuredTool
        import json as _json
        
        extra_tools = []
        for action in ck_actions:
            # Build a passthrough tool for each frontend action
            action_name = action.get("name", "")
            action_desc = action.get("description", "")
            # Create a simple schema from parameters
            params = action.get("parameters", [])
            
            def make_handler(n):
                def handler(**kwargs):
                    return f"Frontend action '{n}' dispatched with args: {_json.dumps(kwargs)[:200]}"
                return handler
            
            try:
                t = StructuredTool.from_function(
                    func=make_handler(action_name),
                    name=action_name,
                    description=action_desc,
                )
                extra_tools.append(t)
            except Exception:
                pass
        
        if extra_tools:
            combined_llm = llm.bind_tools(tools + extra_tools)
        else:
            combined_llm = llm_with_tools
    else:
        combined_llm = llm_with_tools

    # Configure CopilotKit to emit tool calls to frontend
    ck_config = copilotkit_customize_config(config, emit_tool_calls=True, emit_messages=True)

    try:
        response = await combined_llm.ainvoke(final_messages, config=ck_config)
    except Exception as exc:
        if not _is_context_limit_error(exc):
            raise
        logger.warning(
            "Prompt exceeded model context (~%d tokens). Retrying with aggressive trimming.",
            estimated_prompt_tokens,
        )
        final_messages = _prepare_messages_for_model(
            full_system,
            canvas_ctx,
            filtered,
            max_input_tokens=max(3000, DEFAULT_MAX_INPUT_TOKENS // 2),
            response_token_reserve=max(750, DEFAULT_RESPONSE_TOKEN_RESERVE // 2),
            message_char_limit=900,
            tool_char_limit=450,
            last_human_char_limit=1800,
        )
        response = await combined_llm.ainvoke(final_messages, config=ck_config)
    logger.debug("chatbot_node tool_calls=%s", [tc.get("name") for tc in getattr(response, "tool_calls", [])])

    # Log to Langfuse
    log_generation(final_messages, response, llm_model)

    # Workflow proposal check
    proposal = engine.end_turn()
    if proposal and f"workflow-proposal-{proposal.workflow_id}" not in _canvas_state:
        _canvas_state[f"workflow-proposal-{proposal.workflow_id}"] = {
            "summary": f"workflow proposal: {proposal.name}"
        }
        proposal_note = HumanMessage(content=(
            f"[SYSTEM] Call emit_ui now: surface_id='workflow-proposal-{proposal.workflow_id}', "
            f"components={json.dumps(engine.to_proposal_components(proposal))}, "
            f"grid={{\"w\": 5, \"h\": 4}}. Then say: '{proposal.description}'"
        ))
        extra = await combined_llm.ainvoke(
            [SystemMessage(content=full_system), proposal_note], config=ck_config
        )
        return {"messages": [response, extra], "ui_event": None, "needs_ui": False}

    return {"messages": [response], "ui_event": None, "needs_ui": False}


# ── Automatic memory extraction (runs after each non-system turn) ─────────

# Patterns that indicate storable facts
_PREFERENCE_PATTERNS = [
    (r"\b(?:i (?:prefer|like|want|love|hate|don'?t like|always|never))\b", "fact"),
    (r"\b(?:i (?:am |'m )?interested in)\b", "fact"),  # "I am interested in stock alerts"
    (r"\b(?:notify me|alert me|tell me about|keep me (?:updated|informed))\b", "fact"),
    (r"\b(?:remind me|don'?t forget|remember that|note that)\b", "reminder"),
    (r"\b(?:i decided|we agreed|the plan is|going with)\b", "episode"),
    (r"\b(?:my (?:favorite|preferred|usual))\b", "fact"),
    (r"\b(?:dismiss|skip|ignore|don'?t show)\b", "fact"),
    (r"\b(?:schedule|meeting|call) (?:with|about|for)\b", "episode"),
]


async def _extract_and_store_memories(user_msg: str, agent_response_text: str):
    """Extract meaningful facts from conversation and store to memory.
    Runs async, non-blocking, best-effort."""
    if not user_msg or user_msg.startswith("[SYSTEM]"):
        return
    # Skip very short messages (greetings, etc.)
    if len(user_msg.strip()) < 15:
        return

    try:
        from memory import get_memory_manager
        mgr = get_memory_manager()

        # Check user message for storable patterns
        msg_lower = user_msg.lower()
        for pattern, mem_type in _PREFERENCE_PATTERNS:
            if re.search(pattern, msg_lower):
                # Store the user's statement as a memory
                mgr.store(
                    content=user_msg.strip(),
                    memory_type=mem_type,
                    tags=["auto_extracted", "user_statement"],
                )
                logger.debug("Auto-stored [%s]: %s", mem_type, user_msg[:60])
                break  # One memory per turn is enough

        # If agent confirmed storing something or user made a decision, store the exchange
        if agent_response_text:
            resp_lower = agent_response_text.lower()
            if any(phrase in resp_lower for phrase in [
                "i'll remember", "got it", "noted", "stored",
                "dismissed", "skipping", "won't show",
            ]):
                mgr.store(
                    content=f"User: {user_msg.strip()}\nAstra: {agent_response_text[:200]}",
                    memory_type="episode",
                    tags=["auto_extracted", "confirmed_action"],
                )
                logger.debug("Auto-stored confirmed exchange: %s", user_msg[:60])

    except Exception as e:
        logger.debug("Memory extraction failed (non-critical): %s", e)


async def tool_node(state: GraphState, config: RunnableConfig):
    """Run tools. If any data tool ran, set needs_ui=True for the next chatbot turn.
    If emit_ui was called, extract the surface data and push it into ui_event state."""
    last = state["messages"][-1]
    called_tools = []
    if hasattr(last, "tool_calls"):
        engine = get_workflow_engine()
        for tc in last.tool_calls:
            name = tc.get("name", "unknown")
            called_tools.append(name)
            engine.log_action(name)

    result = await _builtin_tool_node.ainvoke(state)

    # Did any data tool run? If so, next chatbot turn needs the UI catalog
    ran_data_tool = any(t in DATA_TOOLS for t in called_tools)
    result["needs_ui"] = ran_data_tool

    # If emit_ui was called, extract the latest surface and push to ui_event state
    # so the frontend can read it via useCoAgent
    if "emit_ui" in called_tools:
        # Find the emit_ui tool call args from the last AI message
        for tc in last.tool_calls:
            if tc.get("name") == "emit_ui":
                args = tc.get("args", {})
                ui_event = {
                    "surface_id": args.get("surface_id", ""),
                    "components": args.get("components", []),
                    "grid": args.get("grid"),
                }
                result["ui_event"] = ui_event
                # Emit state immediately so frontend gets it during streaming
                try:
                    await copilotkit_emit_state(config, {"ui_event": ui_event})
                except Exception as e:
                    logger.debug("copilotkit_emit_state failed (non-critical): %s", e)
                break

    return result


def should_continue(state: GraphState) -> Literal["tools", "memory_extract"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "memory_extract"


async def memory_extract_node(state: GraphState):
    """Post-response: extract facts from conversation and store to memory."""
    messages = state["messages"]

    # Find last human message and last AI response
    last_human = ""
    last_ai = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and not last_ai:
            content = m.content
            if isinstance(content, list):
                content = "".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in content
                )
            last_ai = content or ""
        elif isinstance(m, HumanMessage) and not last_human:
            last_human = m.content if isinstance(m.content, str) else ""
        if last_human and last_ai:
            break

    if last_human:
        try:
            await _extract_and_store_memories(last_human, last_ai)
        except Exception:
            pass  # Never break the graph

    return state


# ── Graph assembly ────────────────────────────────────────────────────────────

memory_saver = MemorySaver()

builder = StateGraph(GraphState)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)
builder.add_node("memory_extract", memory_extract_node)
builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", should_continue)
builder.add_edge("tools", "chatbot")
builder.add_edge("memory_extract", END)

graph = builder.compile(checkpointer=memory_saver)


async def get_agent_response_stream(user_input: str, conversation_id: str = "default"):
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "needs_ui": False,
    }
    config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 50}
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        yield event
