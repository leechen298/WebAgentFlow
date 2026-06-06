"""add learned_capabilities table

Revision ID: 20260605_0001
Revises: df9ed1494afd
Create Date: 2026-06-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260605_0001"
down_revision: str | None = "df9ed1494afd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learned_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_template", sa.String(length=512), nullable=False),
        sa.Column(
            "query_signature",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("dom_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("capability_key", sa.String(length=255), nullable=False),
        sa.Column("capability_kind", sa.String(length=64), nullable=False),
        sa.Column("human_label", sa.String(length=255), nullable=True),
        sa.Column("region_ref", sa.String(length=255), nullable=False),
        sa.Column("control_ref", sa.String(length=512), nullable=False),
        sa.Column("adapter_type", sa.String(length=64), nullable=False),
        sa.Column("action_schema_json", sa.JSON(), nullable=False),
        sa.Column("sample_value_policy_json", sa.JSON(), nullable=False),
        sa.Column("terminal_target_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column(
            "provenance",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'system'"),
        ),
        sa.Column(
            "trust",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'provisional'"),
        ),
        sa.Column("trust_reason", sa.Text(), nullable=True),
        sa.Column("trust_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column("source_learned_path_id", sa.String(length=36), nullable=True),
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
        sa.UniqueConstraint(
            "dedup_key", name="uq_learned_capabilities_dedup_key"
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["exploration_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_learned_path_id"],
            ["learned_paths.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_learned_capabilities_page_kind",
        "learned_capabilities",
        ["page_template", "capability_kind"],
    )
    op.create_index(
        "ix_learned_capabilities_trust",
        "learned_capabilities",
        ["trust"],
    )
    op.create_index(
        "ix_learned_capabilities_source_run",
        "learned_capabilities",
        ["source_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learned_capabilities_source_run", table_name="learned_capabilities"
    )
    op.drop_index("ix_learned_capabilities_trust", table_name="learned_capabilities")
    op.drop_index(
        "ix_learned_capabilities_page_kind", table_name="learned_capabilities"
    )
    op.drop_table("learned_capabilities")
