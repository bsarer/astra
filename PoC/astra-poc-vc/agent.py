import os
import json
import logging
from typing import Annotated, Literal, TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

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

# Canvas state: surface_id -> summary
_canvas_state: dict[str, dict] = {}
_processed_email_ids: set[str] = set()

# Tools that return data and MUST be followed by emit_ui
DATA_TOOLS = {
    "list_user_files", "read_user_file", "search_user_files",
    "list_emails", "get_email", "search_emails",
    "list_calendar_events", "get_calendar_event",
    "get_stock_quote", "get_watchlist_summary", "get_stock_history", "analyze_stock_email_context",
    "get_upcoming_trip", "get_weather", "get_currency_exchange",
}


def get_canvas_context() -> str:
    if not _canvas_state:
        return "Canvas is empty."
    lines = ["Current canvas surfaces:"]
    for sid, info in _canvas_state.items():
        lines.append(f"  - {sid}: {info.get('summary', 'unknown')}")
    return "\n".join(lines)


def get_processed_emails_context() -> str:
    if not _processed_email_ids:
        return ""
    return f"Already processed email IDs (skip these): {', '.join(sorted(_processed_email_ids))}"


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    ui_event: dict | None
    # Flag: did the last tool call return data that needs rendering?
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
    SparklineChart, CalendarEvent, Clock
    """
    comp_types = [c.get("type", "?") for c in components[:5]]
    summary = f"{len(components)} components ({', '.join(comp_types)})"
    _canvas_state[surface_id] = {"summary": summary, "component_count": len(components)}
    return f"Surface '{surface_id}' rendered. Canvas: {len(_canvas_state)} surface(s)."


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


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def chatbot_node(state: GraphState):
    messages = state["messages"]
    needs_ui = state.get("needs_ui", False)

    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
    )

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

    system_parts.append(f"\n### Canvas State:\n{canvas_ctx}")
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
    final_messages = [SystemMessage(content=full_system)] + filtered

    response = await llm_with_tools.ainvoke(final_messages)
    logger.debug("chatbot_node tool_calls=%s", [tc.get("name") for tc in getattr(response, "tool_calls", [])])

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
        extra = await llm_with_tools.ainvoke(
            [SystemMessage(content=full_system), proposal_note]
        )
        return {"messages": [response, extra], "ui_event": None, "needs_ui": False}

    return {"messages": [response], "ui_event": None, "needs_ui": False}


async def tool_node(state: GraphState):
    """Run tools. If any data tool ran, set needs_ui=True for the next chatbot turn."""
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
    return result


def should_continue(state: GraphState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


# ── Graph assembly ────────────────────────────────────────────────────────────

memory_saver = MemorySaver()

builder = StateGraph(GraphState)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)
builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", should_continue)
builder.add_edge("tools", "chatbot")

graph = builder.compile(checkpointer=memory_saver)


async def get_agent_response_stream(user_input: str, conversation_id: str = "default"):
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "needs_ui": False,
    }
    config = {"configurable": {"thread_id": conversation_id}}
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        yield event
