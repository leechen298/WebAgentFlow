"""add composition_candidates table

Revision ID: 20260607_0001
Revises: 20260605_0002
Create Date: 2026-06-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260607_0001"
down_revision: str | None = "20260605_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "composition_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=96), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("target_scope_ref", sa.String(length=96), nullable=False),
        sa.Column("page_template", sa.String(length=512), nullable=False),
        sa.Column("query_signature", sa.JSON(), nullable=False),
        sa.Column("dom_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("candidate_family", sa.String(length=64), nullable=False),
        sa.Column("source_capability_ids_json", sa.JSON(), nullable=False),
        sa.Column("ordered_capability_kinds_json", sa.JSON(), nullable=False),
        sa.Column("expected_terminal_target_json", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("generation_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("static_rejection_reason", sa.Text(), nullable=True),
        sa.Column("execution_outcome_json", sa.JSON(), nullable=False),
        sa.Column("promotion_decision_json", sa.JSON(), nullable=False),
        sa.Column("negative_evidence_json", sa.JSON(), nullable=False),
        sa.Column("learning_batch_id", sa.String(length=36), nullable=True),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column("promoted_learned_path_id", sa.String(length=36), nullable=True),
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
        sa.UniqueConstraint("candidate_id", name="uq_composition_candidates_candidate_id"),
    )
    op.create_index(
        "ix_composition_candidates_page_family",
        "composition_candidates",
        ["page_template", "candidate_family"],
    )
    op.create_index(
        "ix_composition_candidates_status",
        "composition_candidates",
        ["status"],
    )
    op.create_index(
        "ix_composition_candidates_batch",
        "composition_candidates",
        ["learning_batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_composition_candidates_batch", table_name="composition_candidates")
    op.drop_index("ix_composition_candidates_status", table_name="composition_candidates")
    op.drop_index(
        "ix_composition_candidates_page_family",
        table_name="composition_candidates",
    )
    op.drop_table("composition_candidates")
