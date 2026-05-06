"""add learned_paths table (delivery phase 10 · iter 01)

Ships the ``learned_paths`` table that stores reusable exploration
outcomes. Populated automatically on ``pass_gate = pass`` runs by
``exploration``'s ``_persist_autonomous_run`` → ingest hook.

See docs/iterations/phase-10/01-learned-path-persistence for intent
and design.

Revision ID: 20260424_0001
Revises: 20260420_0001
Create Date: 2026-04-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_0001"
down_revision: str | None = "20260420_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learned_paths",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_template", sa.String(length=512), nullable=False),
        sa.Column("query_signature", sa.JSON(), nullable=False),
        sa.Column("dom_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("scenario", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.String(length=16), nullable=False),
        sa.Column("trust", sa.String(length=16), nullable=False),
        sa.Column("trust_reason", sa.Text(), nullable=True),
        sa.Column("trust_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
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
        sa.UniqueConstraint("dedup_key", name="uq_learned_paths_dedup_key"),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["exploration_runs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_learned_paths_page_template_scenario",
        "learned_paths",
        ["page_template", "scenario"],
    )
    op.create_index("ix_learned_paths_trust", "learned_paths", ["trust"])


def downgrade() -> None:
    op.drop_index("ix_learned_paths_trust", table_name="learned_paths")
    op.drop_index(
        "ix_learned_paths_page_template_scenario", table_name="learned_paths"
    )
    op.drop_table("learned_paths")
