"""add operator review columns to exploration_runs

Adds run-level operator review status independent of LearnedPath trust.

Revision ID: 20260502_0001
Revises: 20260424_0002
Create Date: 2026-05-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260502_0001"
down_revision: str | None = "20260424_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("exploration_runs") as batch:
        batch.add_column(
            sa.Column(
                "operator_review_status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'unreviewed'"),
            )
        )
        batch.add_column(
            sa.Column(
                "operator_review_note",
                sa.Text(),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "operator_reviewed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("exploration_runs") as batch:
        batch.drop_column("operator_reviewed_at")
        batch.drop_column("operator_review_note")
        batch.drop_column("operator_review_status")
