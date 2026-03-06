import uuid
import pytest
from session import SessionManager


class TestSessionManagerGetOrCreate:
    def test_generates_uuid_when_none(self):
        mgr = SessionManager()
        sid = mgr.get_or_create(None)
        # Should be a valid UUID
        uuid.UUID(sid)

    def test_returns_same_id_on_second_call(self):
        mgr = SessionManager()
        sid = mgr.get_or_create(None)
        assert mgr.get_or_create(sid) == sid

    def test_returns_provided_id_first_time(self):
        mgr = SessionManager()
        sid = mgr.get_or_create("my-session")
        assert sid == "my-session"

    def test_returns_provided_id_on_resume(self):
        mgr = SessionManager()
        mgr.get_or_create("abc-123")
        assert mgr.get_or_create("abc-123") == "abc-123"

    def test_multiple_none_calls_produce_unique_ids(self):
        mgr = SessionManager()
        ids = {mgr.get_or_create(None) for _ in range(50)}
        assert len(ids) == 50


class TestSessionManagerGetConfig:
    def test_returns_correct_config(self):
        mgr = SessionManager()
        config = mgr.get_config("sess-1")
        assert config == {"configurable": {"thread_id": "sess-1"}}

    def test_thread_id_matches_session_id(self):
        mgr = SessionManager()
        sid = mgr.get_or_create(None)
        config = mgr.get_config(sid)
        assert config["configurable"]["thread_id"] == sid
