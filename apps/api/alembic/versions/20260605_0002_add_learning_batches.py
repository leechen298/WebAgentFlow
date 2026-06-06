"""add learning_batches table

Revision ID: 20260605_0002
Revises: 20260605_0001
Create Date: 2026-06-05 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260605_0002"
down_revision: str | None = "20260605_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("page_template", sa.String(length=512), nullable=True),
        sa.Column(
            "query_signature",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("dom_fingerprint", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column(
            "planned_scenarios_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "summary_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_run_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "created_capability_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "created_learned_path_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_learning_batches_session_status",
        "learning_batches",
        ["session_id", "status"],
    )
    op.create_index(
        "ix_learning_batches_status",
        "learning_batches",
        ["status"],
    )
    op.create_index(
        "ix_learning_batches_created_at",
        "learning_batches",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_learning_batches_created_at", table_name="learning_batches")
    op.drop_index("ix_learning_batches_status", table_name="learning_batches")
    op.drop_index("ix_learning_batches_session_status", table_name="learning_batches")
    op.drop_table("learning_batches")
