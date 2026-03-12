import os
import json
import asyncio
from typing import Annotated, Literal, TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Load API keys from .env
load_dotenv()

# Prompt loader utility
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def load_prompt(name: str) -> str:
    """Loads a prompt from the prompts directory."""
    with open(os.path.join(PROMPTS_DIR, f"{name}.md"), "r", encoding="utf-8") as f:
        return f.read().strip()

# --- Canvas state tracking (persisted via checkpointer) ---
# Maps surface_id -> summary of what's rendered (type, key data)
_canvas_state: dict[str, dict] = {}
# Set of email IDs already processed for stock alerts
_processed_email_ids: set[str] = set()


def get_canvas_context() -> str:
    """Build a context string describing what's currently on the canvas."""
    if not _canvas_state:
        return "Canvas is empty — no widgets rendered yet."
    lines = ["Current canvas surfaces:"]
    for sid, info in _canvas_state.items():
        lines.append(f"  - {sid}: {info.get('summary', 'unknown')}")
    return "\n".join(lines)


def get_processed_emails_context() -> str:
    """Build a context string for already-processed email IDs."""
    if not _processed_email_ids:
        return ""
    return f"Already processed email IDs (do NOT re-alert): {', '.join(sorted(_processed_email_ids))}"


# Define the State schema for LangGraph
class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    ui_event: dict | None

# Load prompts from files (system + A2UI catalog + design system + persona)
SYSTEM_PROMPT = (
    load_prompt("system") + "\n\n" +
    load_prompt("a2ui_catalog") + "\n\n" +
    load_prompt("design_system") + "\n\n" +
    load_prompt("persona_context")
)

@tool
def install_python_packages(package_names: List[str]) -> str:
    """Installs one or more Python packages using pip dynamically. 
    Use this if you need a library that is not currently installed (like yfinance, requests, pandas, etc)."""
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + package_names)
        return f"Successfully installed: {', '.join(package_names)}"
    except subprocess.CalledProcessError as e:
        return f"Failed to install packages. Error: {e}"

@tool
def render_widget(id: str, html: str, width_percent: int, height_px: int) -> str:
    """Renders a dynamic HTML widget on the user's left-hand screen.
    Provide an ID, the HTML structure, and requested width (1-100 percent) and height (exact pixels).
    CRITICAL: Always set height_px large enough so your widget doesn't require scrolling! (e.g. 400 or 500 for a calculator)"""
    return f"Widget {id} successfully rendered to the user's workspace."


@tool
def run_python_code(code: str) -> str:
    """Executes a python code snippet safely in an isolated environment (simulated).
    Use this to fulfill backend requirements on the fly (e.g. hitting an API, getting current time, doing math).
    The code should print() the final output you want to receive, or it should be the last expression."""
    import sys
    from io import StringIO
    from concurrent.futures import ThreadPoolExecutor, TimeoutError

    TIMEOUT_SECONDS = 30

    def _execute_code(code: str) -> str:
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        local_env = {}
        try:
            exec(code, {}, local_env)
            output = redirected_output.getvalue()
            if not output and 'result' in local_env:
                output = str(local_env['result'])
        except Exception as e:
            output = f"Error executing code: {e}"
        finally:
            sys.stdout = old_stdout
        return output

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_code, code)
            return future.result(timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        return f"Error: Code execution timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error executing code: {e}"


@tool
def emit_ui(surface_id: str, components: list[dict], grid: dict | None = None) -> str:
    """Emit a declarative UI surface using A2UI components.

    Args:
        surface_id: Unique identifier for this surface (e.g., "stock-alert", "mike-dashboard").
        components: Flat list of A2UI components in adjacency list format.
            Each component: {"id": str, "type": str, "props": dict, "children": list[str]}
            The first component is the root unless specified otherwise.
        grid: Optional layout hints {"w": int (1-12 columns), "h": int (row units)}.

    Returns:
        Confirmation string.
    """
    # Track what's on the canvas
    comp_types = [c.get("type", "?") for c in components[:5]]
    summary = f"{len(components)} components ({', '.join(comp_types)})"
    _canvas_state[surface_id] = {"summary": summary, "component_count": len(components)}
    return f"Surface '{surface_id}' emitted with {len(components)} components. Canvas now has {len(_canvas_state)} surface(s)."


from tools_email_calendar import email_calendar_tools
from tools_travel import travel_tools
from tools_stock import stock_tools

# Available tools
tools = [run_python_code, install_python_packages, render_widget, emit_ui] + email_calendar_tools + travel_tools + stock_tools
_builtin_tool_node = ToolNode(tools)

# Initialize LLM
llm_model = os.getenv("OPENAI_MODEL", os.getenv("MODEL", "gpt-4o-mini"))
llm_base_url = os.getenv("OPENAI_BASE_URL")
llm_api_key = os.getenv("OPENAI_API_KEY")

llm_kwargs = {
    "model": llm_model,
    "temperature": 0.7,
    "streaming": True
}

# Add base_url and api_key only if they exist in env (otherwise it uses defaults)
if llm_base_url:
    llm_kwargs["base_url"] = llm_base_url
if llm_api_key:
    llm_kwargs["api_key"] = llm_api_key

llm = ChatOpenAI(**llm_kwargs)
llm_with_tools = llm.bind_tools(tools)

# Define Graph Nodes
async def chatbot_node(state: GraphState):
    """The main reasoning node for the agent."""
    messages = state["messages"]
    
    # Build dynamic system prompt with canvas state awareness
    canvas_ctx = get_canvas_context()
    email_ctx = get_processed_emails_context()
    dynamic_context = f"\n\n### Current Canvas State:\n{canvas_ctx}"
    if email_ctx:
        dynamic_context += f"\n\n### Processed Emails:\n{email_ctx}"
    
    full_system = SYSTEM_PROMPT + dynamic_context
    
    # Prepend system prompt if not present, or replace existing one
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    messages = [SystemMessage(content=full_system)] + filtered
        
    response = await llm_with_tools.ainvoke(messages)
    
    return {"messages": [response], "ui_event": None}

async def tool_node(state: GraphState):
    """Executes the specified tools using LangGraph's built-in ToolNode."""
    return await _builtin_tool_node.ainvoke(state)

def should_continue(state: GraphState) -> Literal["tools", "__end__"]:
    """Determines whether to jump to the tool node or finish."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"

# Memory Checkpointer
memory = MemorySaver()

# Build Graph
builder = StateGraph(GraphState)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", should_continue)
builder.add_edge("tools", "chatbot")

# Compile graph
graph = builder.compile(checkpointer=memory)

async def get_agent_response_stream(user_input: str, conversation_id: str = "default"):
    """
    Simulates sending a message and streaming the events back.
    """
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    
    config = {"configurable": {"thread_id": conversation_id}}
    
    # Stream the graph execution
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        yield event
