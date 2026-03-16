import os
import json
import logging
from typing import Literal, List
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

logger = logging.getLogger("astra.agent")

# ── Langfuse tracing ──────────────────────────────────────────────────────────
# Set LANGFUSE_ENABLED=1 to log every LLM call: full context, token counts, latency.
_lf = None
_lf_traces: dict[str, any] = {}  # session_id -> active trace
if os.getenv("LANGFUSE_ENABLED", "0") == "1":
    try:
        from langfuse import Langfuse
        _lf = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://host.docker.internal:3000"),
        )
        logger.info("Langfuse tracing enabled")
    except Exception as e:
        logger.warning("Langfuse init failed (non-critical): %s", e)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    if not text:
        return 0
    return len(text) // 4


def _extract_token_usage(response) -> dict:
    """Extract token usage from various LangChain response formats."""
    # Try response_metadata first (OpenAI format)
    meta = getattr(response, "response_metadata", {}) or {}
    usage = meta.get("usage") or meta.get("token_usage") or {}

    # Also check usage_metadata (newer LangChain)
    usage_meta = getattr(response, "usage_metadata", {}) or {}

    input_tokens = (
        usage.get("prompt_tokens") or
        usage.get("input_tokens") or
        usage_meta.get("input_tokens") or
        0
    )
    output_tokens = (
        usage.get("completion_tokens") or
        usage.get("output_tokens") or
        usage_meta.get("output_tokens") or
        0
    )

    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
    }

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


from copilotkit.langgraph import CopilotKitState, copilotkit_customize_config, copilotkit_emit_state
from langchain_core.runnables import RunnableConfig

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
    SparklineChart, CalendarEvent, Clock
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

_llm_callbacks = []
llm = ChatOpenAI(**llm_kwargs)
llm_with_tools = llm.bind_tools(tools)


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def chatbot_node(state: GraphState, config: RunnableConfig):
    messages = state["messages"]
    needs_ui = state.get("needs_ui", False)

    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
    )

    # ── Initial connection: CopilotKit sends messages=[] on first connect ──
    # Emit the dashboard immediately without calling the LLM.
    if not messages or not last_human:
        from langchain_core.messages import AIMessage as _AIMessage
        import datetime as _dt
        hour = _dt.datetime.now().hour
        greeting_time = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
        dashboard_components = [
            {"id": "root", "type": "Column", "props": {"gap": "16px"}, "children": ["greeting", "stats-row", "actions"]},
            {"id": "greeting", "type": "Card", "props": {"variant": "glass"}, "children": ["greet-text", "greet-sub"]},
            {"id": "greet-text", "type": "Text", "props": {"text": f"Good {greeting_time}, Mike 👋", "variant": "title", "weight": "bold"}, "children": []},
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
        grid = {"w": 7, "h": 6}
        ui_event = {"surface_id": "mike-dashboard", "components": dashboard_components, "grid": grid}
        _canvas_state["mike-dashboard"] = {"summary": "dashboard", "component_count": len(dashboard_components)}
        try:
            await copilotkit_emit_state(config, {"ui_event": ui_event})
        except Exception as e:
            logger.debug("copilotkit_emit_state failed: %s", e)
        greeting_msg = _AIMessage(content=f"Good {greeting_time}, Mike! Your dashboard is ready.")
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

    system_parts.append(f"\n### Canvas State:\n{canvas_ctx}")
    if email_ctx:
        system_parts.append(f"\n### Processed Emails:\n{email_ctx}")

    # Domain-aware memory injection (non-blocking)
    # Track context breakdown for observability
    _ctx_breakdown = {
        "base_system_chars": len(BASE_SYSTEM),
        "ui_catalog_chars": len(UI_CATALOG) if needs_ui else 0,
        "canvas_ctx_chars": len(canvas_ctx),
        "email_ctx_chars": len(email_ctx) if email_ctx else 0,
        "memory_ctx_chars": 0,
        "memories_retrieved": 0,
        "files_retrieved": 0,
        "domains": [],
    }
    try:
        if last_human and not (isinstance(last_human, str) and last_human.startswith("[SYSTEM]")):
            from domain_router import classify
            from memory import get_memory_manager
            domains = classify(last_human).domains
            _ctx_breakdown["domains"] = domains
            mgr = get_memory_manager()
            memories = mgr.retrieve(last_human, domains=domains, limit=3)
            files = mgr.search_files(last_human, domains=domains, limit=2)
            _ctx_breakdown["memories_retrieved"] = len(memories)
            _ctx_breakdown["files_retrieved"] = len(files)
            mem_ctx = mgr.format_for_prompt(memories, files)
            if mem_ctx:
                _ctx_breakdown["memory_ctx_chars"] = len(mem_ctx)
                system_parts.append(f"\n{mem_ctx}")
    except Exception:
        pass

    full_system = "\n\n".join(system_parts)
    _ctx_breakdown["total_system_chars"] = len(full_system)
    _ctx_breakdown["estimated_system_tokens"] = _estimate_tokens(full_system)
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    final_messages = [SystemMessage(content=full_system)] + filtered

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

    response = await combined_llm.ainvoke(final_messages, config=ck_config)
    logger.debug("chatbot_node tool_calls=%s", [tc.get("name") for tc in getattr(response, "tool_calls", [])])

    # Log to Langfuse: full context, token counts, model, context breakdown
    if _lf:
        try:
            # Extract token usage from response
            token_usage = _extract_token_usage(response)
            model_name = getattr(response, "response_metadata", {}).get("model_name", llm_model)

            # If no token counts from API, estimate from content
            if token_usage["input"] == 0:
                total_input_chars = sum(
                    len(m.content) if isinstance(m.content, str) else len(json.dumps(m.content))
                    for m in final_messages
                )
                token_usage["input"] = _estimate_tokens(str(total_input_chars))
                token_usage["estimated"] = True
            if token_usage["output"] == 0:
                out_content = response.content if isinstance(response.content, str) else json.dumps(response.content)
                token_usage["output"] = _estimate_tokens(out_content)
                token_usage["estimated"] = True
            token_usage["total"] = token_usage["input"] + token_usage["output"]

            def _msg_to_dict(m):
                role = m.type if hasattr(m, "type") else "user"
                role = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}.get(role, role)
                content = m.content if isinstance(m.content, str) else json.dumps(m.content)
                return {"role": role, "content": content}

            # Extract tool calls if any
            tool_calls = []
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = [{"name": tc.get("name"), "args": tc.get("args", {})} for tc in response.tool_calls]

            # Get session ID from config
            session_id = config.get("configurable", {}).get("thread_id", "unknown")

            # Create or get trace for this session
            trace = _lf.trace(
                name="astra_turn",
                session_id=session_id,
                user_id="mike",  # persona
                tags=["astra", trigger],
                metadata={
                    "trigger": trigger,
                    "needs_ui": needs_ui,
                },
            )

            # Log the generation with full context breakdown
            trace.generation(
                name="chatbot_llm",
                model=model_name,
                input=[_msg_to_dict(m) for m in final_messages],
                output=response.content if isinstance(response.content, str) else json.dumps(response.content),
                usage=token_usage,
                metadata={
                    "context_breakdown": _ctx_breakdown,
                    "tool_calls": tool_calls,
                    "message_count": len(final_messages),
                    "system_prompt_tokens_est": _ctx_breakdown.get("estimated_system_tokens", 0),
                },
            )

            # Log context components as spans for detailed analysis
            trace.span(
                name="context_injection",
                metadata={
                    "base_system_tokens": _estimate_tokens(BASE_SYSTEM),
                    "ui_catalog_tokens": _estimate_tokens(UI_CATALOG) if needs_ui else 0,
                    "memory_tokens": _estimate_tokens(str(_ctx_breakdown.get("memory_ctx_chars", 0))),
                    "memories_count": _ctx_breakdown.get("memories_retrieved", 0),
                    "files_count": _ctx_breakdown.get("files_retrieved", 0),
                    "domains": _ctx_breakdown.get("domains", []),
                    "total_context_chars": _ctx_breakdown.get("total_system_chars", 0),
                },
            )

            _lf.flush()
        except Exception as e:
            logger.debug("Langfuse log failed (non-critical): %s", e)

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
import re

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
    import time
    last = state["messages"][-1]
    called_tools = []
    tool_args = {}
    if hasattr(last, "tool_calls"):
        engine = get_workflow_engine()
        for tc in last.tool_calls:
            name = tc.get("name", "unknown")
            called_tools.append(name)
            tool_args[name] = tc.get("args", {})
            engine.log_action(name)

    start_time = time.time()
    result = await _builtin_tool_node.ainvoke(state)
    elapsed_ms = (time.time() - start_time) * 1000

    # Log tool executions to Langfuse
    if _lf and called_tools:
        try:
            session_id = config.get("configurable", {}).get("thread_id", "unknown")
            trace = _lf.trace(
                name="tool_execution",
                session_id=session_id,
                user_id="mike",
                tags=["astra", "tools"],
            )
            for tool_name in called_tools:
                trace.span(
                    name=f"tool:{tool_name}",
                    metadata={
                        "tool_name": tool_name,
                        "args": tool_args.get(tool_name, {}),
                        "is_data_tool": tool_name in DATA_TOOLS,
                    },
                )
            trace.update(metadata={
                "tools_called": called_tools,
                "duration_ms": round(elapsed_ms, 2),
                "tool_count": len(called_tools),
            })
            _lf.flush()
        except Exception as e:
            logger.debug("Langfuse tool log failed: %s", e)

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
    config = {"configurable": {"thread_id": conversation_id}}
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        yield event
