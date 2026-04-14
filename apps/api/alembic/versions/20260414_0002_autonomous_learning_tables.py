"""autonomous learning tables

Revision ID: 20260414_0002
Revises: 20260317_0001
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260414_0002"
down_revision: str | None = "20260317_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "success_criteria",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("strength", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
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
    op.create_table(
        "learned_paths",
        sa.Column("page_signature", sa.String(length=512), nullable=True),
        sa.Column("goal_type", sa.String(length=64), nullable=True),
        sa.Column("success_criteria_id", sa.String(length=36), nullable=True),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("variable_slots_json", sa.JSON(), nullable=False),
        sa.Column("observed_effects_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("user_labels_json", sa.JSON(), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["success_criteria_id"],
            ["success_criteria.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
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
    op.drop_table("learned_paths")
    op.drop_table("success_criteria")
