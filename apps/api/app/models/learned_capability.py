"""LearnedCapability ORM — atomic page-operation learning assets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.learned_path import (
    Provenance,
    TrustStatus,
)


class LearnedCapability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learned_capabilities"
    __table_args__ = (
        UniqueConstraint(
            "dedup_key", name="uq_learned_capabilities_dedup_key"
        ),
    )

    page_template: Mapped[str] = mapped_column(String(512), nullable=False)
    query_signature: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    dom_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_key: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    human_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    control_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_schema_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    sample_value_policy_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    terminal_target_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[Provenance] = mapped_column(
        String(16),
        nullable=False,
        default=Provenance.SYSTEM,
        server_default=text("'system'"),
    )
    trust: Mapped[TrustStatus] = mapped_column(
        String(16),
        nullable=False,
        default=TrustStatus.PROVISIONAL,
        server_default=text("'provisional'"),
    )
    trust_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("exploration_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_learned_path_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("learned_paths.id", ondelete="SET NULL"),
        nullable=True,
    )
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
