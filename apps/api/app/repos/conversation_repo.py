"""M11.0 conversation session repository.

Pure data access — no LLM calls, no replay execution, no autonomous runs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationEvent, ConversationMessage, ConversationSession

_UNSET = object()


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Session lifecycle ──────────────────────────────────────────────

    def create_session(
        self,
        initial_status: str = "idle",
        current_mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        session = ConversationSession(
            status=initial_status,
            current_mode=current_mode,
            metadata_json=metadata or {},
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self.session.get(ConversationSession, session_id)

    def update_session_status(
        self,
        session_id: str,
        status: str,
        previous_status: str | None = _UNSET,
        current_mode: str | None = _UNSET,
        metadata_patch: dict[str, Any] | None = None,
    ) -> ConversationSession:
        session = self.session.get(ConversationSession, session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        session.status = status
        if previous_status is not _UNSET:
            session.previous_status = previous_status
        if current_mode is not _UNSET:
            session.current_mode = current_mode
        if metadata_patch:
            session.metadata_json = {**session.metadata_json, **metadata_patch}

        self.session.commit()
        self.session.refresh(session)
        return session

    # ── Messages ───────────────────────────────────────────────────────

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata or {},
            created_at=datetime.now(UTC),
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_messages(
        self,
        session_id: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_transcript(self, session_id: str) -> list[ConversationMessage]:
        """Return messages ordered by created_at (user-facing transcript)."""
        return self.list_messages(session_id, limit=10_000)

    # ── Events ─────────────────────────────────────────────────────────

    def append_event(
        self,
        session_id: str,
        type: str,
        payload: dict[str, Any] | None = None,
    ) -> ConversationEvent:
        event = ConversationEvent(
            session_id=session_id,
            type=type,
            payload_json=payload or {},
            created_at=datetime.now(UTC),
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_events(
        self,
        session_id: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[ConversationEvent]:
        stmt = (
            select(ConversationEvent)
            .where(ConversationEvent.session_id == session_id)
            .order_by(ConversationEvent.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
