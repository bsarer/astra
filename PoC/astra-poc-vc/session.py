import uuid


class SessionManager:
    """Thin wrapper around LangGraph's MemorySaver checkpointer.

    The session_id maps directly to LangGraph's thread_id — no additional
    persistence layer is needed because MemorySaver already handles
    conversation state.
    """

    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def get_or_create(self, session_id: str | None = None) -> str:
        """Return *session_id* if it already exists, or generate a new UUID."""
        if session_id and session_id in self._sessions:
            return session_id
        new_id = session_id if session_id else str(uuid.uuid4())
        self._sessions.add(new_id)
        return new_id

    def get_config(self, session_id: str) -> dict:
        """Return the LangGraph config dict for this session."""
        return {"configurable": {"thread_id": session_id}}
