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
from langgraph.checkpoint.memory import MemorySaver

# Load API keys from .env
load_dotenv()

# Prompt loader utility
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def load_prompt(name: str) -> str:
    """Loads a prompt from the prompts directory."""
    with open(os.path.join(PROMPTS_DIR, f"{name}.md"), "r", encoding="utf-8") as f:
        return f.read().strip()

# Define the State schema for LangGraph
class GraphState(TypedDict):
    # 'messages' will hold the conversation history
    # We use add_messages reducer to append new messages automatically
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 'ui_components' will hold the ephemeral GenUI components the agent wants to display
    # This is heavily scoped as a dict replacing old ones for now, or just an event dispatch
    # Simple dictionary to hold the last requested UI injection
    ui_event: dict | None

# Load prompts from files (system + design system are merged into one)
SYSTEM_PROMPT = load_prompt("system") + "\n\n" + load_prompt("design_system")

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
    # For PoC, we are simply executing it via exec and capturing stdout.
    import sys
    from io import StringIO
    
    # Redirect stdout
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

# Available tools
tools = [run_python_code, install_python_packages, render_widget]

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
    
    # Prepend system prompt if not present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    response = await llm_with_tools.ainvoke(messages)
    
    return {"messages": [response], "ui_event": None}

async def tool_node(state: GraphState):
    """Executes the specified tools."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_map = {t.name: t for t in tools}
        tool_responses = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            if tool_name in tool_map:
                try:
                    res = await tool_map[tool_name].ainvoke(tool_args)
                    tool_responses.append(ToolMessage(content=str(res), tool_call_id=tool_call["id"]))
                except Exception as e:
                    tool_responses.append(ToolMessage(content=str(e), tool_call_id=tool_call["id"]))
                    
        return {"messages": tool_responses}
    return {"messages": []}

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
