import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from threading import Lock

from app.schemas.chat import HistoryMessage, CitationItem, ChatHistoryResponse


class SessionService:
    def __init__(self):
        self._sessions: Dict[str, List[HistoryMessage]] = {}
        self._lock = Lock()

    def get_or_create_session_id(self, session_id: Optional[str] = None) -> str:
        if not session_id or not session_id.strip():
            return f"sess_{uuid.uuid4()}"
        return session_id.strip()

    def add_user_message(self, session_id: str, content: str) -> HistoryMessage:
        msg = HistoryMessage(
            id=f"msg_user_{uuid.uuid4().hex[:8]}",
            role="user",
            content=content,
            citations=None,
            timestamp=datetime.now(timezone.utc)
        )
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(msg)
        return msg

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        citations: Optional[List[CitationItem]] = None
    ) -> HistoryMessage:
        msg = HistoryMessage(
            id=f"msg_ai_{uuid.uuid4().hex[:8]}",
            role="assistant",
            content=content,
            citations=citations or [],
            timestamp=datetime.now(timezone.utc)
        )
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(msg)
        return msg

    def get_history(self, session_id: str) -> ChatHistoryResponse:
        with self._lock:
            messages = self._sessions.get(session_id, [])
            return ChatHistoryResponse(
                session_id=session_id,
                total_messages=len(messages),
                messages=list(messages)
            )


session_service = SessionService()
