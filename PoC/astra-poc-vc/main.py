"""Astra backend — FastAPI server with CopilotKit AG-UI, WebSocket, and REST endpoints."""

import os
import json
import logging
import asyncio
import uuid as _uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from agent import get_agent_response_stream, graph
from agent import _canvas_state
from session import SessionManager
from copilotkit import LangGraphAGUIAgent
from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from email_poller import run_email_poller
from stock_streamer import ensure_started as start_stock_streamer, subscribe as stock_subscribe
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

load_dotenv()

DEBUG = os.getenv("DEBUG", "0") == "1"
logger = logging.getLogger("astra")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
if DEBUG:
    logger.setLevel(logging.DEBUG)

# ── App state ─────────────────────────────────────────────────────────────────
_ready = False
_active_connections: dict[str, WebSocket] = {}
_seen_email_ids: set[str] = set()
_session_locks: dict[str, asyncio.Lock] = {}
EMAIL_POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "300"))
session_manager = SessionManager()


def _get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


# ── Stream helpers (shared by WS + REST) ──────────────────────────────────────

def _extract_text(chunk_content) -> str:
    """Extract plain text from a LangChain chunk content (str or list of blocks)."""
    if isinstance(chunk_content, str):
        return chunk_content
    if isinstance(chunk_content, list):
        return "".join(
            b.get("text", "") if isinstance(b, dict) else str(b)
            for b in chunk_content
        )
    return ""


def _build_widget_msg(tool_input: dict) -> WidgetMessage:
    """Build a WidgetMessage from render_widget tool input."""
    grid: GridOptions = {}
    if "width_percent" in tool_input:
        grid["w"] = max(1, min(12, int(tool_input["width_percent"] * 12 / 100)))
    if "height_px" in tool_input:
        grid["h"] = max(1, int(int(tool_input["height_px"]) / 10))
    return {
        "type": "widget",
        "id": tool_input.get("id", "widget"),
        "html": tool_input.get("html", ""),
        "grid": grid,
    }


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ready
    try:
        from tools_files import index_all_files
        indexed = index_all_files()
        logger.info("Startup: indexed %d user files", indexed)
    except Exception as e:
        logger.warning("File indexing failed (non-critical): %s", e)
    _ready = True
    start_stock_streamer()
    poller_task = asyncio.create_task(
        run_email_poller(
            active_connections=_active_connections,
            seen_email_ids=_seen_email_ids,
            get_session_lock=_get_session_lock,
            handle_user_message=_handle_user_message,
            poll_interval=EMAIL_POLL_INTERVAL,
        )
    )
    yield
    poller_task.cancel()


app = FastAPI(title="Astra AI Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── CopilotKit / AG-UI Endpoint ──────────────────────────────────────────────

_agui_agent = LangGraphAGUIAgent(
    name="astra_agent",
    description="Astra AI assistant with email, calendar, stock, and travel tools.",
    graph=graph,
)

_copilotkit_info = {
    "agents": {"astra_agent": {"description": _agui_agent.description or ""}},
    "actions": {},
    "version": "0.1.78",
}


def _parse_agent_input(payload: dict) -> RunAgentInput:
    """Build RunAgentInput from a CopilotKit payload dict."""
    return RunAgentInput(
        thread_id=payload.get("threadId", payload.get("thread_id", str(_uuid.uuid4()))),
        run_id=payload.get("runId", payload.get("run_id", str(_uuid.uuid4()))),
        state=payload.get("state", {}),
        messages=payload.get("messages", []),
        tools=payload.get("tools", []),
        context=payload.get("context", []),
        forwarded_props=payload.get("forwardedProps", payload.get("forwarded_props", {})),
    )


@app.api_route("/api/copilotkit", methods=["GET", "POST"])
async def copilotkit_single_endpoint(request: Request):
    """Single-endpoint CopilotKit handler (info + agent execution)."""
    if request.method == "GET":
        return JSONResponse(_copilotkit_info)

    body = await request.json()
    method = body.get("method", "")
    logger.info("CopilotKit POST method=%s", method)

    if method == "info" or not method:
        return JSONResponse(_copilotkit_info)

    if method.startswith("agent/"):
        payload = body.get("body") or body.get("params", {})
        agent_input = _parse_agent_input(payload)
        logger.info("CopilotKit agent run: thread=%s msgs=%d", agent_input.thread_id, len(agent_input.messages))
        encoder = EventEncoder(accept=request.headers.get("accept", ""))

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
    if not path.startswith("agent/"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    body = await request.json()
    agent_input = _parse_agent_input(body)
    encoder = EventEncoder(accept=request.headers.get("accept", ""))

    async def event_generator():
        async for event in _agui_agent.run(agent_input):
            yield encoder.encode(event)

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    if not _ready:
        return JSONResponse({"status": "initializing"}, status_code=503)
    return {"status": "ok"}


# ── Stock Live SSE ────────────────────────────────────────────────────────────

@app.get("/api/stocks/live")
async def stocks_live_sse():
    """SSE stream of live stock watchlist data, refreshed every 60s."""
    return StreamingResponse(stock_subscribe(), media_type="text/event-stream")


# ── Surface close (frontend → backend canvas sync) ───────────────────────────

class SurfaceCloseRequest(BaseModel):
    surface_id: str

@app.post("/api/surface/close")
async def surface_close(req: SurfaceCloseRequest):
    """Remove a surface from the agent's canvas state when user closes a widget."""
    removed = _canvas_state.pop(req.surface_id, None)
    logger.debug("Surface closed: %s (was_tracked=%s)", req.surface_id, removed is not None)
    return {"ok": True, "removed": removed is not None}


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str | None = None):
    await websocket.accept()
    sid = session_manager.get_or_create(session_id)

    init_msg: SessionInitMessage = {"type": "session_init", "session_id": sid}
    await websocket.send_text(serialize_server_message(init_msg))

    _active_connections[sid] = websocket

    # Lightweight greeting
    await _handle_user_message(
        websocket,
        "[SYSTEM] Session started. Greet Mike briefly (one sentence) and tell him "
        "you're loading his dashboard in the background. Do NOT call any tools yet.",
        sid,
    )

    # Background dashboard fetch
    async def _background_fetch():
        await asyncio.sleep(0.5)
        ws = _active_connections.get(sid)
        if not ws:
            return
        async with _get_session_lock(sid):
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
            try:
                msg = parse_client_message(raw)
            except ValueError as exc:
                err: ErrorMessage = {"type": "error", "content": str(exc)}
                await websocket.send_text(serialize_server_message(err))
                continue

            async with _get_session_lock(sid):
                if msg["type"] == "user_message":
                    await _handle_user_message(websocket, msg["content"], sid)
                elif msg["type"] == "widget_event":
                    await _handle_widget_event(websocket, msg["event_name"], msg["payload"], sid)

    except WebSocketDisconnect:
        _active_connections.pop(sid, None)
        _session_locks.pop(sid, None)


# ── WS stream handlers ───────────────────────────────────────────────────────

async def _stream_agent_to_ws(websocket: WebSocket, content: str, session_id: str) -> None:
    """Core streaming loop: invoke agent and forward tokens/widgets to WebSocket."""
    content_buffer = ""
    async for event in get_agent_response_stream(content, conversation_id=session_id):
        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                text = _extract_text(chunk.content)
                if text:
                    content_buffer += text
                    await websocket.send_text(serialize_server_message({"type": "token", "content": text}))

        elif kind == "on_tool_start" and name == "render_widget":
            widget_msg = _build_widget_msg(event["data"].get("input", {}))
            await websocket.send_text(serialize_server_message(widget_msg))

        elif kind == "on_chain_end" and name == "chatbot":
            node_output = event["data"].get("output", {})
            msgs = node_output.get("messages", [])
            if msgs:
                last = msgs[-1]
                if hasattr(last, "content") and last.content and not content_buffer:
                    text = _extract_text(last.content)
                    if text:
                        await websocket.send_text(serialize_server_message({"type": "token", "content": text}))
                if hasattr(last, "tool_calls") and last.tool_calls:
                    for tc in last.tool_calls:
                        if tc.get("name") == "render_widget":
                            widget_msg = _build_widget_msg(tc.get("args", {}))
                            await websocket.send_text(serialize_server_message(widget_msg))


async def _handle_user_message(websocket: WebSocket, content: str, session_id: str) -> None:
    """Invoke agent and stream back, with error handling and done signal."""
    try:
        await _stream_agent_to_ws(websocket, content, session_id)
    except Exception as exc:
        err_msg: ErrorMessage = {"type": "error", "content": f"Agent error: {exc}"}
        await websocket.send_text(serialize_server_message(err_msg))
    await websocket.send_text(serialize_server_message({"type": "done"}))


async def _handle_widget_event(
    websocket: WebSocket, event_name: str, payload: dict, session_id: str
) -> None:
    """Forward a widget event to the agent."""
    human_text = json.dumps({"widget_event": event_name, "payload": payload})
    try:
        await _stream_agent_to_ws(websocket, human_text, session_id)
    except Exception as exc:
        err_msg: ErrorMessage = {"type": "error", "content": f"Agent error: {exc}"}
        await websocket.send_text(serialize_server_message(err_msg))
    await websocket.send_text(serialize_server_message({"type": "done"}))


# ── Legacy REST chat endpoint ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Legacy SSE chat endpoint — preserved for backward compatibility."""
    async def event_generator():
        content_buffer = ""
        try:
            async for event in get_agent_response_stream(request.message, conversation_id="session_4"):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        text = _extract_text(chunk.content)
                        if text:
                            content_buffer += text
                            yield f"data: {json.dumps({'type': 'message', 'content': text})}\n\n"

                elif kind == "on_tool_start" and name == "render_widget":
                    tool_input = event["data"].get("input", {})
                    widget = _build_widget_msg(tool_input)
                    yield f"data: {json.dumps({'type': 'ui_component', 'component': widget})}\n\n"

                elif kind == "on_chain_end" and name == "chatbot":
                    msgs = event["data"].get("output", {}).get("messages", [])
                    if msgs:
                        last = msgs[-1]
                        if hasattr(last, "content") and last.content and not content_buffer:
                            text = _extract_text(last.content)
                            if text:
                                yield f"data: {json.dumps({'type': 'message', 'content': text})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'message', 'content': f'[Error: {e}]'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Static files + root ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
