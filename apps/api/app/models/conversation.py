"""M11.0 runtime conversation ORM models.

Persistent store for conversation sessions, messages, and events.
No user / account / tenant fields — this is not an identity system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_sessions"
    __table_args__ = (Index("ix_conversation_sessions_updated_at", "updated_at"),)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="idle",
    )
    current_mode: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at.asc()",
    )
    events: Mapped[list[ConversationEvent]] = relationship(
        "ConversationEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationEvent.created_at.asc()",
    )


class ConversationMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index("ix_conversation_messages_session_id_created_at", "session_id", "created_at"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    session: Mapped[ConversationSession] = relationship(
        "ConversationSession", back_populates="messages"
    )


class ConversationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        Index("ix_conversation_events_session_id_created_at", "session_id", "created_at"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    session: Mapped[ConversationSession] = relationship(
        "ConversationSession", back_populates="events"
    )
