"""Tests for health check and WebSocket endpoints in main.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

import main as main_module
from main import app


# ---------------------------------------------------------------------------
# Health check tests (Req 7.1, 7.2, 7.3)
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.anyio
    async def test_returns_200_when_ready(self):
        main_module._ready = True
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_returns_503_while_initializing(self):
        main_module._ready = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["status"] == "initializing"
        # Restore
        main_module._ready = True


# ---------------------------------------------------------------------------
# WebSocket tests (Req 1.1–1.8, 8.1–8.4)
# ---------------------------------------------------------------------------

def _make_token_event(text: str):
    """Create a mock on_chat_model_stream event."""
    chunk = MagicMock()
    chunk.content = text
    return {"event": "on_chat_model_stream", "name": "", "data": {"chunk": chunk}}


def _make_tool_start_event(widget_id: str, html: str, width_pct: int, height_px: int):
    """Create a mock on_tool_start event for render_widget."""
    return {
        "event": "on_tool_start",
        "name": "render_widget",
        "data": {
            "input": {
                "id": widget_id,
                "html": html,
                "width_percent": width_pct,
                "height_px": height_px,
            }
        },
    }


class TestWebSocketSessionInit:
    @pytest.mark.anyio
    async def test_sends_session_init_on_connect(self):
        """Connecting to /ws should immediately receive a session_init message (Req 8.4)."""
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                data = json.loads(ws.receive_text())
                assert data["type"] == "session_init"
                assert "session_id" in data

    @pytest.mark.anyio
    async def test_resumes_session_with_provided_id(self):
        """Providing session_id query param should resume that session (Req 8.3)."""
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/ws?session_id=my-sess-42") as ws:
                data = json.loads(ws.receive_text())
                assert data["type"] == "session_init"
                assert data["session_id"] == "my-sess-42"


class TestWebSocketMalformedJson:
    @pytest.mark.anyio
    async def test_malformed_json_returns_error_keeps_open(self):
        """Sending non-JSON should return an error and keep the connection open (Req 1.7)."""
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                # Consume session_init
                ws.receive_text()
                # Send garbage
                ws.send_text("not valid json {{{")
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "error"
                assert len(resp["content"]) > 0
                # Connection should still be open — send another bad message
                ws.send_text("still broken")
                resp2 = json.loads(ws.receive_text())
                assert resp2["type"] == "error"


class TestWebSocketUserMessage:
    @pytest.mark.anyio
    async def test_token_and_done_messages(self):
        """A user_message should produce token messages and a final done (Req 1.4, 1.6)."""
        from starlette.testclient import TestClient

        events = [_make_token_event("Hello"), _make_token_event(" world")]

        async def fake_stream(user_input, conversation_id):
            for e in events:
                yield e

        with patch("main.get_agent_response_stream", side_effect=fake_stream):
            with TestClient(app) as client:
                with client.websocket_connect("/ws") as ws:
                    ws.receive_text()  # session_init
                    ws.send_text(json.dumps({"type": "user_message", "content": "hi"}))

                    msg1 = json.loads(ws.receive_text())
                    assert msg1 == {"type": "token", "content": "Hello"}

                    msg2 = json.loads(ws.receive_text())
                    assert msg2 == {"type": "token", "content": " world"}

                    msg3 = json.loads(ws.receive_text())
                    assert msg3 == {"type": "done"}

    @pytest.mark.anyio
    async def test_widget_message(self):
        """A render_widget tool start should produce a widget message (Req 1.5)."""
        from starlette.testclient import TestClient

        events = [_make_tool_start_event("w1", "<b>hi</b>", 50, 300)]

        async def fake_stream(user_input, conversation_id):
            for e in events:
                yield e

        with patch("main.get_agent_response_stream", side_effect=fake_stream):
            with TestClient(app) as client:
                with client.websocket_connect("/ws") as ws:
                    ws.receive_text()  # session_init
                    ws.send_text(json.dumps({"type": "user_message", "content": "make widget"}))

                    msg = json.loads(ws.receive_text())
                    assert msg["type"] == "widget"
                    assert msg["id"] == "w1"
                    assert msg["html"] == "<b>hi</b>"
                    assert msg["grid"]["w"] == 6  # 50 * 12 / 100 = 6
                    assert msg["grid"]["h"] == 30  # 300 / 10 = 30

                    done = json.loads(ws.receive_text())
                    assert done["type"] == "done"

    @pytest.mark.anyio
    async def test_agent_exception_sends_error_then_done(self):
        """An unhandled agent exception should send error then done (Req 1.8)."""
        from starlette.testclient import TestClient

        async def failing_stream(user_input, conversation_id):
            raise RuntimeError("boom")
            yield  # make it a generator  # noqa: E501

        with patch("main.get_agent_response_stream", side_effect=failing_stream):
            with TestClient(app) as client:
                with client.websocket_connect("/ws") as ws:
                    ws.receive_text()  # session_init
                    ws.send_text(json.dumps({"type": "user_message", "content": "crash"}))

                    err = json.loads(ws.receive_text())
                    assert err["type"] == "error"
                    assert "boom" in err["content"]

                    done = json.loads(ws.receive_text())
                    assert done["type"] == "done"
