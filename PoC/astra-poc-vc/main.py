import os
import json
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent import get_agent_response_stream
from session import SessionManager
from models import (
    serialize_server_message,
    parse_client_message,
    TokenMessage,
    WidgetMessage,
    GridOptions,
    DoneMessage,
    ErrorMessage,
    SessionInitMessage,
)

# Load environment variables
load_dotenv()

# App-level readiness flag for health check (Req 7.3)
_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ready
    _ready = True
    yield


app = FastAPI(title="LangChain GenUI Web Agent PoC", lifespan=lifespan)

# Shared session manager
session_manager = SessionManager()


# --- Health Check (Req 7.1, 7.2, 7.3) ---

@app.get("/health")
async def health_check():
    """Returns 200 when the server is ready, 503 while initializing."""
    if not _ready:
        return JSONResponse({"status": "initializing"}, status_code=503)
    return {"status": "ok"}


# --- WebSocket Endpoint (Req 1.1–1.8, 5.1, 5.2, 8.1–8.4) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str | None = None):
    """
    Accepts a WebSocket connection. Reads JSON messages from the client,
    dispatches to the LangGraph agent, and streams responses back.
    """
    await websocket.accept()

    # Create or resume session (Req 8.1, 8.3, 8.4)
    sid = session_manager.get_or_create(session_id)

    # Send session_init message on connect
    init_msg: SessionInitMessage = {"type": "session_init", "session_id": sid}
    await websocket.send_text(serialize_server_message(init_msg))

    try:
        while True:
            raw = await websocket.receive_text()

            # Parse incoming message (Req 1.7 — malformed JSON)
            try:
                msg = parse_client_message(raw)
            except ValueError as exc:
                err: ErrorMessage = {"type": "error", "content": str(exc)}
                await websocket.send_text(serialize_server_message(err))
                continue

            if msg["type"] == "user_message":
                await _handle_user_message(websocket, msg["content"], sid)

            elif msg["type"] == "widget_event":
                await _handle_widget_event(
                    websocket, msg["event_name"], msg["payload"], sid
                )

    except WebSocketDisconnect:
        pass


async def _handle_user_message(
    websocket: WebSocket, content: str, session_id: str
) -> None:
    """Invoke the LangGraph agent and stream typed messages back."""
    config = session_manager.get_config(session_id)
    content_buffer = ""

    try:
        async for event in get_agent_response_stream(content, conversation_id=session_id):
            kind = event["event"]
            name = event.get("name", "")

            # Streaming tokens (Req 1.4)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    if isinstance(text, list):
                        text = "".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in text
                        )
                    if text:
                        content_buffer += text
                        token_msg: TokenMessage = {"type": "token", "content": text}
                        await websocket.send_text(serialize_server_message(token_msg))

            # Widget tool invocation (Req 1.5)
            elif kind == "on_tool_start" and name == "render_widget":
                tool_input = event["data"].get("input", {})
                grid: GridOptions = {}
                if "width_percent" in tool_input:
                    grid["w"] = max(1, min(12, int(tool_input["width_percent"] * 12 / 100)))
                if "height_px" in tool_input:
                    grid["h"] = max(1, int(int(tool_input["height_px"]) / 10))

                widget_msg: WidgetMessage = {
                    "type": "widget",
                    "id": tool_input.get("id", "widget"),
                    "html": tool_input.get("html", ""),
                    "grid": grid,
                }
                await websocket.send_text(serialize_server_message(widget_msg))

            # Fallback for non-streaming LLMs
            elif kind == "on_chain_end" and name == "chatbot":
                node_output = event["data"].get("output", {})
                if "messages" in node_output and node_output["messages"]:
                    last_message = node_output["messages"][-1]

                    if hasattr(last_message, "content") and last_message.content and not content_buffer:
                        text = last_message.content
                        if isinstance(text, list):
                            text = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in text
                            )
                        if text:
                            token_msg = {"type": "token", "content": text}
                            await websocket.send_text(serialize_server_message(token_msg))

                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tcall in last_message.tool_calls:
                            if tcall.get("name") == "render_widget":
                                args = tcall.get("args", {})
                                grid = {}
                                if "width_percent" in args:
                                    grid["w"] = max(1, min(12, int(args["width_percent"] * 12 / 100)))
                                if "height_px" in args:
                                    grid["h"] = max(1, int(int(args["height_px"]) / 10))
                                widget_msg = {
                                    "type": "widget",
                                    "id": args.get("id", "widget"),
                                    "html": args.get("html", ""),
                                    "grid": grid,
                                }
                                await websocket.send_text(serialize_server_message(widget_msg))

    except Exception as exc:
        # Unhandled exception during agent processing (Req 1.8)
        err_msg: ErrorMessage = {"type": "error", "content": f"Agent error: {exc}"}
        await websocket.send_text(serialize_server_message(err_msg))

    # Always send done to signal stream completion (Req 1.6)
    done_msg: DoneMessage = {"type": "done"}
    await websocket.send_text(serialize_server_message(done_msg))


async def _handle_widget_event(
    websocket: WebSocket, event_name: str, payload: dict, session_id: str
) -> None:
    """Forward a widget event to the agent as a HumanMessage with event context."""
    human_text = json.dumps({"widget_event": event_name, "payload": payload})
    try:
        async for event in get_agent_response_stream(human_text, conversation_id=session_id):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    if isinstance(text, list):
                        text = "".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in text
                        )
                    if text:
                        token_msg: TokenMessage = {"type": "token", "content": text}
                        await websocket.send_text(serialize_server_message(token_msg))

            elif kind == "on_tool_start" and name == "render_widget":
                tool_input = event["data"].get("input", {})
                grid: GridOptions = {}
                if "width_percent" in tool_input:
                    grid["w"] = max(1, min(12, int(tool_input["width_percent"] * 12 / 100)))
                if "height_px" in tool_input:
                    grid["h"] = max(1, int(int(tool_input["height_px"]) / 10))
                widget_msg: WidgetMessage = {
                    "type": "widget",
                    "id": tool_input.get("id", "widget"),
                    "html": tool_input.get("html", ""),
                    "grid": grid,
                }
                await websocket.send_text(serialize_server_message(widget_msg))

    except Exception as exc:
        err_msg: ErrorMessage = {"type": "error", "content": f"Agent error: {exc}"}
        await websocket.send_text(serialize_server_message(err_msg))

    done_msg: DoneMessage = {"type": "done"}
    await websocket.send_text(serialize_server_message(done_msg))


# --- Backward-compatible POST /chat endpoint ---

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams LangGraph events and captures GenUI components.
    Preserved temporarily for backward compatibility.
    """
    user_message = request.message

    async def event_generator():
        content_buffer = ""

        try:
            async for event in get_agent_response_stream(user_message, conversation_id="session_4"):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, list):
                            content = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in content
                            )
                        if content:
                            content_buffer += content
                            yield f"data: {json.dumps({'type': 'message', 'content': content})}\n\n"

                elif kind == "on_tool_start" and name == "render_widget":
                    tool_input = event["data"].get("input", {})
                    widget_data = {
                        "id": tool_input.get("id", "widget"),
                        "html": tool_input.get("html", ""),
                        "grid": {},
                    }
                    if "width_percent" in tool_input:
                        widget_data["grid"]["w"] = max(1, min(12, int(tool_input["width_percent"] * 12 / 100)))
                    if "height_px" in tool_input:
                        widget_data["grid"]["h"] = max(1, int(int(tool_input["height_px"]) / 10))
                    yield f"data: {json.dumps({'type': 'ui_component', 'component': widget_data})}\n\n"

                elif kind == "on_chain_end" and name == "chatbot":
                    node_output = event["data"].get("output", {})
                    if "messages" in node_output and node_output["messages"]:
                        last_message = node_output["messages"][-1]
                        if hasattr(last_message, "content") and last_message.content and not content_buffer:
                            content = last_message.content
                            if isinstance(content, list):
                                content = "".join(
                                    block.get("text", "") if isinstance(block, dict) else str(block)
                                    for block in content
                                )
                            if content:
                                yield f"data: {json.dumps({'type': 'message', 'content': content})}\n\n"
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            for tcall in last_message.tool_calls:
                                if tcall.get("name") == "render_widget":
                                    args = tcall.get("args", {})
                                    widget_data = {
                                        "id": args.get("id", "widget"),
                                        "html": args.get("html", ""),
                                        "grid": {},
                                    }
                                    if "width_percent" in args:
                                        widget_data["grid"]["w"] = max(1, min(12, int(args["width_percent"] * 12 / 100)))
                                    if "height_px" in args:
                                        widget_data["grid"]["h"] = max(1, int(int(args["height_px"]) / 10))
                                    yield f"data: {json.dumps({'type': 'ui_component', 'component': widget_data})}\n\n"

        except Exception as e:
            print(f"Exception in graph stream: {e}")
            error_msg = f"\n\n[Error: {e}]"
            yield f"data: {json.dumps({'type': 'message', 'content': error_msg})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Startup event: set readiness flag ---

# --- Static file serving and root page (Req 5.1, 5.2) ---
# IMPORTANT: Mount AFTER all route definitions so /health and /ws take priority.

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main frontend page."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
