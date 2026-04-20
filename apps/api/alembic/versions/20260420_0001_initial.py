"""initial schema — autonomous exploration only

After the legacy-stack cleanup (recordings / skills / runs /
learned_paths / success_criteria / candidate_feedbacks all gone),
``exploration_runs`` is the only table the app writes to.

This migration replaces the earlier 0001/0002/0003 trio and is the
new baseline. Any dev DB that still holds the old tables should be
rebuilt via ``docker compose -f infra/docker/docker-compose.yml
down -v && up -d`` before applying this migration.

Revision ID: 20260420_0001
Revises:
Create Date: 2026-04-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260420_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exploration_runs",
        sa.Column("page_signature", sa.String(length=512), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("success_criteria_ids_json", sa.JSON(), nullable=False),
        sa.Column("strategy_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("result_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("candidate_elements_json", sa.JSON(), nullable=True),
        sa.Column("interaction_hints_json", sa.JSON(), nullable=True),
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


def downgrade() -> None:
    op.drop_table("exploration_runs")
