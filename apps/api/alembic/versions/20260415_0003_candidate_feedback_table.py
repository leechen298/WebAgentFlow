"""candidate feedback table

Revision ID: 20260415_0003
Revises: 20260414_0002
Create Date: 2026-04-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_0003"
down_revision: str | None = "20260414_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_feedbacks",
        sa.Column("recording_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("element_key", sa.String(length=512), nullable=False),
        sa.Column("judgment", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("inferred_actions_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
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
        "ix_candidate_feedbacks_recording",
        "candidate_feedbacks",
        ["recording_id", "element_key", "run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_feedbacks_recording", table_name="candidate_feedbacks")
    op.drop_table("candidate_feedbacks")
