"""M11.0 conversation session repository.

Pure data access — no LLM calls, no replay execution, no autonomous runs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationEvent, ConversationMessage, ConversationSession
from app.schemas.conversation import ConversationEventType, ConversationRole, ConversationStatus

_UNSET = object()


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Session lifecycle ──────────────────────────────────────────────

    def create_session(
        self,
        initial_status: str | ConversationStatus = ConversationStatus.IDLE,
        current_mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        status = _validate_enum_value("initial_status", initial_status, ConversationStatus)
        session = ConversationSession(
            status=status,
            current_mode=current_mode,
            metadata_json=metadata or {},
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self.session.get(ConversationSession, session_id)

    def list_sessions(
        self,
        current_mode: str | None = None,
        status: str | ConversationStatus | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        limit: int = 50,
    ) -> list[ConversationSession]:
        stmt = (
            select(ConversationSession)
            .order_by(ConversationSession.updated_at.desc())
            .limit(limit)
        )
        if current_mode is not None:
            stmt = stmt.where(ConversationSession.current_mode == current_mode)
        if status is not None:
            status_value = _validate_enum_value("status", status, ConversationStatus)
            stmt = stmt.where(ConversationSession.status == status_value)
        if updated_from is not None:
            stmt = stmt.where(ConversationSession.updated_at >= updated_from)
        if updated_to is not None:
            stmt = stmt.where(ConversationSession.updated_at <= updated_to)
        return list(self.session.scalars(stmt).all())

    def count_messages(self, session_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
        )
        return self.session.scalar(stmt) or 0

    def count_events(self, session_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(ConversationEvent)
            .where(ConversationEvent.session_id == session_id)
        )
        return self.session.scalar(stmt) or 0

    def get_last_message_by_role(
        self, session_id: str, role: str | ConversationRole
    ) -> ConversationMessage | None:
        role_value = _validate_enum_value("role", role, ConversationRole)
        stmt = (
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.role == role_value,
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def update_session_status(
        self,
        session_id: str,
        status: str | ConversationStatus,
        previous_status: str | ConversationStatus | None = _UNSET,
        current_mode: str | None = _UNSET,
        metadata_patch: dict[str, Any] | None = None,
    ) -> ConversationSession:
        validated_status = _validate_enum_value("status", status, ConversationStatus)
        session = self.session.get(ConversationSession, session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        session.status = validated_status
        if previous_status is not _UNSET:
            session.previous_status = (
                None
                if previous_status is None
                else _validate_enum_value(
                    "previous_status",
                    previous_status,
                    ConversationStatus,
                )
            )
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
        role: str | ConversationRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        self._require_session(session_id)
        role_value = _validate_enum_value("role", role, ConversationRole)
        message = ConversationMessage(
            session_id=session_id,
            role=role_value,
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
        _reject_cursor(cursor)
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
        type: str | ConversationEventType,
        payload: dict[str, Any] | None = None,
    ) -> ConversationEvent:
        self._require_session(session_id)
        type_value = _validate_enum_value("type", type, ConversationEventType)
        event = ConversationEvent(
            session_id=session_id,
            type=type_value,
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
        _reject_cursor(cursor)
        stmt = (
            select(ConversationEvent)
            .where(ConversationEvent.session_id == session_id)
            .order_by(ConversationEvent.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def _require_session(self, session_id: str) -> ConversationSession:
        session = self.session.get(ConversationSession, session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        return session


def _validate_enum_value(
    field_name: str,
    value: str | ConversationStatus | ConversationRole | ConversationEventType,
    enum_type: type[ConversationStatus] | type[ConversationRole] | type[ConversationEventType],
) -> str:
    try:
        return enum_type(value).value
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value}") from exc


def _reject_cursor(cursor: str | None) -> None:
    if cursor is not None:
        raise ValueError("cursor pagination is not implemented yet")
