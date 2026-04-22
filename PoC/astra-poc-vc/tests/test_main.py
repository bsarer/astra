"""Tests for health check and WebSocket endpoints in main.py."""

import sys
import os
import base64
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


class TestFileApi:
    @pytest.mark.anyio
    async def test_lists_and_previews_files(self, monkeypatch, tmp_path):
        pricing = tmp_path / "Pricing_Brief.md"
        pricing.write_text("# Pricing\nAcme pricing and discount summary.", encoding="utf-8")
        (tmp_path / "Images").mkdir()
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            list_resp = await client.get("/api/files", params={"query": "pricing"})
            assert list_resp.status_code == 200
            payload = list_resp.json()
            assert payload["file_count"] == 1
            assert payload["count"] == payload["file_count"] + payload["folder_count"]
            assert payload["files"][0]["filename"] == "Pricing_Brief.md"
            assert any(folder["path"] == "Images" for folder in payload["folders"])

            preview_resp = await client.get("/api/files/Pricing_Brief.md/preview")
            assert preview_resp.status_code == 200
            preview = preview_resp.json()
            assert preview["summary_card"]["points"]
            assert preview["path"] == "Pricing_Brief.md"

            open_resp = await client.get("/api/files/Pricing_Brief.md/open")
            assert open_resp.status_code == 200
            opened = open_resp.json()
            assert opened["viewer"]["kind"] == "text"
            assert "pricing" in opened["content"].lower()
            assert opened["analysis"]["mode"] == "text"

    @pytest.mark.anyio
    async def test_rename_move_and_delete_file(self, monkeypatch, tmp_path):
        file_path = tmp_path / "Draft.md"
        file_path.write_text("# Draft\nQuarterly board notes.", encoding="utf-8")
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            rename_resp = await client.post(
                "/api/files/rename",
                json={"path": "Draft.md", "new_name": "Renamed.md"},
            )
            assert rename_resp.status_code == 200
            assert rename_resp.json()["filename"] == "Renamed.md"

            move_resp = await client.post(
                "/api/files/move",
                json={"path": "Renamed.md", "destination_subdirectory": "archive"},
            )
            assert move_resp.status_code == 200
            assert move_resp.json()["path"] == "archive/Renamed.md"

            delete_resp = await client.post(
                "/api/files/delete",
                json={"path": "archive/Renamed.md"},
            )
            assert delete_resp.status_code == 200
            assert delete_resp.json()["deleted"] is True

    @pytest.mark.anyio
    async def test_delete_many_files_api(self, monkeypatch, tmp_path):
        (tmp_path / "A.md").write_text("# A", encoding="utf-8")
        (tmp_path / "B.md").write_text("# B", encoding="utf-8")
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            delete_resp = await client.post(
                "/api/files/delete-many",
                json={"paths": ["A.md", "B.md"]},
            )
            assert delete_resp.status_code == 200
            payload = delete_resp.json()
            assert payload["deleted_count"] == 2
            assert payload["error_count"] == 0
            assert not (tmp_path / "A.md").exists()
            assert not (tmp_path / "B.md").exists()

    @pytest.mark.anyio
    async def test_create_folder_and_browse_subdirectory(self, monkeypatch, tmp_path):
        nested = tmp_path / "Notes"
        nested.mkdir()
        (nested / "Brief.md").write_text("# Brief\nFolder scoped note.", encoding="utf-8")
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/api/files/folder",
                json={"name": "Archive", "parent_subdirectory": ""},
            )
            assert create_resp.status_code == 200
            assert create_resp.json()["path"] == "Archive"

            list_resp = await client.get("/api/files", params={"subdirectory": "Notes"})
            assert list_resp.status_code == 200
            payload = list_resp.json()
            assert payload["current_directory"] == "Notes"
            assert payload["files"][0]["filename"] == "Brief.md"
            assert payload["breadcrumbs"][-1]["path"] == "Notes"
            assert payload["count"] == payload["file_count"] + payload["folder_count"]

    @pytest.mark.anyio
    async def test_delete_folder_api(self, monkeypatch, tmp_path):
        archive = tmp_path / "Archive"
        archive.mkdir()
        (archive / "Brief.md").write_text("# Brief\nFolder scoped note.", encoding="utf-8")
        (archive / "Sub").mkdir()
        (archive / "Sub" / "Draft.md").write_text("# Draft\nnested", encoding="utf-8")
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            delete_resp = await client.post(
                "/api/files/folder/delete",
                json={"path": "Archive", "recursive": True},
            )
            assert delete_resp.status_code == 200
            payload = delete_resp.json()
            assert payload["deleted"] is True
            assert payload["path"] == "Archive"
            assert payload["deleted_file_count"] == 2
            assert not (tmp_path / "Archive").exists()

    @pytest.mark.anyio
    async def test_save_email_attachment_into_files(self, monkeypatch, tmp_path):
        import providers.factory as provider_factory

        attachment_bytes = b"quarterly-report"
        emails_path = tmp_path / "emails.json"
        emails_path.write_text(
            json.dumps(
                [
                    {
                        "id": "mail-1",
                        "from": "ops@example.com",
                        "to": "mike@example.com",
                        "subject": "Quarterly report",
                        "body": "See attached report.",
                        "date": "2026-04-03T09:00:00",
                        "labels": ["inbox"],
                        "read": False,
                        "attachments": [
                            {
                                "filename": "Quarterly_Report.pdf",
                                "content_type": "application/pdf",
                                "size_bytes": len(attachment_bytes),
                                "content_base64": base64.b64encode(attachment_bytes).decode("ascii"),
                            }
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("DATA_PROVIDER", "mock")
        monkeypatch.delenv("MIKE_EMAIL_PROVIDER", raising=False)
        monkeypatch.setattr(provider_factory, "_ROOT", tmp_path)
        monkeypatch.setenv("PERSONA_FILES_DIR", str(tmp_path / "files"))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post(
                "/api/emails/mail-1/attachments/save",
                json={"attachment_name": "Quarterly_Report.pdf", "destination_subdirectory": "Downloads"},
            )
            assert save_resp.status_code == 200
            payload = save_resp.json()
            assert payload["saved_to"] == "Downloads/Quarterly_Report.pdf"

            preview_resp = await client.get("/api/files/Downloads/Quarterly_Report.pdf/preview")
            assert preview_resp.status_code == 200
            preview = preview_resp.json()
            assert preview["filename"] == "Quarterly_Report.pdf"


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
