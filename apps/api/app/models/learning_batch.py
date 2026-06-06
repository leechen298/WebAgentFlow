"""LearningBatch ORM for bounded product learning lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearningBatchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    TIMED_OUT = "timed_out"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"
    UNVERIFIED = "unverified"


TERMINAL_LEARNING_BATCH_STATUSES = frozenset(
    {
        LearningBatchStatus.COMPLETED,
        LearningBatchStatus.PARTIAL_SUCCESS,
        LearningBatchStatus.TIMED_OUT,
        LearningBatchStatus.CANCELLED,
        LearningBatchStatus.FAILED,
        LearningBatchStatus.UNVERIFIED,
    }
)


class LearningBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_batches"
    __table_args__ = (
        Index("ix_learning_batches_session_status", "session_id", "status"),
        Index("ix_learning_batches_status", "status"),
        Index("ix_learning_batches_created_at", "created_at"),
    )

    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_template: Mapped[str | None] = mapped_column(String(512), nullable=True)
    query_signature: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    dom_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[LearningBatchStatus] = mapped_column(
        String(32),
        nullable=False,
        default=LearningBatchStatus.PENDING,
        server_default=text("'pending'"),
    )
    policy_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    planned_scenarios_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    summary_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    created_run_ids_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    created_capability_ids_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    created_learned_path_ids_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
