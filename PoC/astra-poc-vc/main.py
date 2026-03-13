import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent import get_agent_response_stream, graph
from session import SessionManager
from copilotkit import LangGraphAGUIAgent
from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
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

# Debug mode: set DEBUG=1 in .env to log all WS messages
DEBUG = os.getenv("DEBUG", "0") == "1"
logger = logging.getLogger("astra")
# Always show INFO level so we can see CopilotKit request details
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled — all WebSocket messages will be logged")


def _debug_send(session_id: str, data: str):
    if DEBUG:
        logger.debug("WS ⬆ [%s] %s", session_id, data[:300])


def _debug_recv(session_id: str, data: str):
    if DEBUG:
        logger.debug("WS ⬇ [%s] %s", session_id, data[:300])

# App-level readiness flag for health check (Req 7.3)
_ready = False

# Track active WebSocket connections for email polling push
_active_connections: dict[str, WebSocket] = {}  # session_id -> websocket
_seen_email_ids: set[str] = set()  # track already-processed email IDs

# Per-session lock to prevent poller and user messages from interleaving
_session_locks: dict[str, asyncio.Lock] = {}

EMAIL_POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "300"))  # seconds (default 5 min)


def _get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def _email_poller():
    """Background task: polls for new emails and triggers agent for stock-related ones."""
    from providers.factory import get_email_provider

    logger.info("Email poller started (interval=%ds)", EMAIL_POLL_INTERVAL)

    # Wait for first connection
    while not _active_connections:
        await asyncio.sleep(2)

    # Give the background fetch time to seed seen IDs before we start polling
    await asyncio.sleep(10)

    # Seed seen IDs from current inbox (so we don't re-trigger on existing emails)
    try:
        provider = get_email_provider()
        initial = await provider.list_emails(limit=20)
        for e in initial:
            _seen_email_ids.add(e.id)
        logger.info("Email poller seeded with %d existing email IDs", len(_seen_email_ids))
    except Exception as ex:
        logger.warning("Email poller seed failed: %s", ex)

    while True:
        await asyncio.sleep(EMAIL_POLL_INTERVAL)

        if not _active_connections:
            continue

        try:
            provider = get_email_provider()
            emails = await provider.list_emails(limit=10)

            new_emails = [e for e in emails if e.id not in _seen_email_ids]
            if not new_emails:
                continue

            for e in new_emails:
                _seen_email_ids.add(e.id)

            logger.info("Email poller found %d new email(s)", len(new_emails))

            # Process each new email without blocking user messages
            for e in new_emails:
                prompt = (
                    f"[SYSTEM] New email detected by background poller:\n\n"
                    f"From: {e.from_addr}\n"
                    f"Subject: {e.subject}\n"
                    f"Body: {e.body[:500]}\n\n"
                    f"INSTRUCTIONS: Check if this email mentions any stocks from Mike's "
                    f"watchlist (AAPL, MSFT, NVDA, TSLA, GOOG, AMZN, META). "
                    f"If it does, call `analyze_stock_email_context` with the subject and body, "
                    f"then call `get_stock_quote` for each matched ticker, "
                    f"then render a stock alert widget with id 'stock-alert'. "
                    f"If the email is NOT stock-related, just show a brief notification "
                    f"like 'New email from [sender]: [subject]'."
                )

                for sid, ws in list(_active_connections.items()):
                    lock = _get_session_lock(sid)
                    # Use lock so poller waits if user is mid-message
                    try:
                        async with lock:
                            await _handle_user_message(ws, prompt, sid)
                    except Exception as ex:
                        logger.warning("Poller push failed for session %s: %s", sid, ex)

        except Exception as ex:
            logger.warning("Email poller error: %s", ex)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ready
    # Index user files into memory on startup (non-blocking, best-effort)
    try:
        from tools_files import index_all_files
        indexed = index_all_files()
        logger.info("Startup: indexed %d user files", indexed)
    except Exception as e:
        logger.warning("File indexing failed (non-critical): %s", e)
    _ready = True
    poller_task = asyncio.create_task(_email_poller())
    yield
    poller_task.cancel()


app = FastAPI(title="LangChain GenUI Web Agent PoC", lifespan=lifespan)

# CORS middleware for CopilotKit frontend
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared session manager
session_manager = SessionManager()

# --- CopilotKit / AG-UI Endpoint ---
_agui_agent = LangGraphAGUIAgent(
    name="astra_agent",
    description="Astra AI assistant with email, calendar, stock, and travel tools.",
    graph=graph,
)

_copilotkit_info = {
    "agents": {
        "astra_agent": {"description": _agui_agent.description or ""},
    },
    "actions": {},
    "version": "0.1.78",
}


@app.api_route("/api/copilotkit", methods=["GET", "POST"])
async def copilotkit_single_endpoint(request: Request):
    """Single-endpoint CopilotKit handler (info + agent execution)."""
    if request.method == "GET":
        return JSONResponse(_copilotkit_info)

    body = await request.json()
    method = body.get("method", "")
    logger.info("CopilotKit POST method=%s", method)

    # Info / discovery
    if method == "info" or not method:
        return JSONResponse(_copilotkit_info)

    # Agent connect/run — payload is in body["body"], not body["params"]
    if method.startswith("agent/"):
        # CopilotKit sends: {"method": "agent/run", "params": {"agentId": "..."}, "body": {actual payload}}
        payload = body.get("body") or body.get("params", {})
        accept_header = request.headers.get("accept", "")
        encoder = EventEncoder(accept=accept_header)

        import uuid as _uuid
        agent_input = RunAgentInput(
            thread_id=payload.get("threadId", payload.get("thread_id", str(_uuid.uuid4()))),
            run_id=payload.get("runId", payload.get("run_id", str(_uuid.uuid4()))),
            state=payload.get("state", {}),
            messages=payload.get("messages", []),
            tools=payload.get("tools", []),
            context=payload.get("context", []),
            forwarded_props=payload.get("forwardedProps", payload.get("forwarded_props", {})),
        )
        logger.info("CopilotKit agent run: thread=%s msgs=%d", agent_input.thread_id, len(agent_input.messages))

        async def event_generator():
            async for event in _agui_agent.run(agent_input):
                yield encoder.encode(event)

        return StreamingResponse(event_generator(), media_type=encoder.get_content_type())

    return JSONResponse({"error": f"Unknown method: {method}"}, status_code=400)


@app.get("/api/copilotkit/info")
async def copilotkit_info_get():
    return JSONResponse(_copilotkit_info)


@app.post("/api/copilotkit/{path:path}")
async def copilotkit_rest_agent(request: Request, path: str):
    """REST transport fallback: /api/copilotkit/agent/<name>/run"""
    if path.startswith("agent/"):
        body = await request.json()
        accept_header = request.headers.get("accept", "")
        encoder = EventEncoder(accept=accept_header)

        import uuid as _uuid
        agent_input = RunAgentInput(
            thread_id=body.get("threadId", body.get("thread_id", str(_uuid.uuid4()))),
            run_id=body.get("runId", body.get("run_id", str(_uuid.uuid4()))),
            state=body.get("state", {}),
            messages=body.get("messages", []),
            tools=body.get("tools", []),
            context=body.get("context", []),
            forwarded_props=body.get("forwardedProps", body.get("forwarded_props", {})),
        )

        async def event_generator():
            async for event in _agui_agent.run(agent_input):
                yield encoder.encode(event)

        return StreamingResponse(event_generator(), media_type=encoder.get_content_type())

    return JSONResponse({"error": "Not found"}, status_code=404)


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
    payload = serialize_server_message(init_msg)
    _debug_send(sid, payload)
    await websocket.send_text(payload)

    # Register for email polling push BEFORE background task so poller can find us
    _active_connections[sid] = websocket

    # Lightweight greeting — non-blocking, lets user type immediately
    await _handle_user_message(
        websocket,
        "[SYSTEM] Session started. Greet Mike briefly (one sentence) and tell him "
        "you're loading his dashboard in the background. Do NOT call any tools yet.",
        sid,
    )

    # Fire the heavy fetch as a background task so the UI is immediately usable
    async def _background_fetch():
        await asyncio.sleep(0.5)  # small yield so WS loop starts
        if sid not in _active_connections:
            return
        ws = _active_connections.get(sid)
        if not ws:
            return
        lock = _get_session_lock(sid)
        async with lock:
            await _handle_user_message(
                ws,
                "[SYSTEM] Background fetch: now load Mike's dashboard.\n"
                "1. Call `list_emails` — show inbox summary widget (surface_id='inbox-summary')\n"
                "2. Call `list_calendar_events` — show today's schedule widget (surface_id='schedule')\n"
                "3. Call `get_upcoming_trip` — if a trip is found, show a travel widget\n"
                "4. For each email, check if subject/body mentions AAPL, MSFT, NVDA, TSLA, GOOG, AMZN, META. "
                "If any match, call `analyze_stock_email_context` then `get_stock_quote` and render "
                "a stock alert widget (surface_id='stock-alert').\n"
                "Keep chat text to one short summary line. Widgets carry the detail.",
                sid,
            )

    asyncio.create_task(_background_fetch())

    try:
        while True:
            raw = await websocket.receive_text()
            _debug_recv(sid, raw)

            # Parse incoming message (Req 1.7 — malformed JSON)
            try:
                msg = parse_client_message(raw)
            except ValueError as exc:
                err: ErrorMessage = {"type": "error", "content": str(exc)}
                await websocket.send_text(serialize_server_message(err))
                continue

            if msg["type"] == "user_message":
                lock = _get_session_lock(sid)
                async with lock:
                    await _handle_user_message(websocket, msg["content"], sid)

            elif msg["type"] == "widget_event":
                lock = _get_session_lock(sid)
                async with lock:
                    await _handle_widget_event(
                        websocket, msg["event_name"], msg["payload"], sid
                    )

    except WebSocketDisconnect:
        _active_connections.pop(sid, None)
        _session_locks.pop(sid, None)


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
