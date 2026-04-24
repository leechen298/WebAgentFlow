"""set DB-level server_default on learned_paths.provenance / trust

Follow-up to ``20260424_0001`` per codex-review: the first migration
relied on ORM-side defaults only for ``provenance='system'`` and
``trust='provisional'``. Any SQL INSERT that bypasses the ORM (scripts,
backfills, psql, a future shell integration) would violate the table
contract in ``plan.md``. This migration adds the defaults at the DB
level so the contract holds regardless of the insertion path.

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_0002"
down_revision: str | None = "20260424_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("learned_paths") as batch:
        batch.alter_column(
            "provenance",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default=sa.text("'system'"),
        )
        batch.alter_column(
            "trust",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default=sa.text("'provisional'"),
        )


def downgrade() -> None:
    with op.batch_alter_table("learned_paths") as batch:
        batch.alter_column(
            "provenance",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default=None,
        )
        batch.alter_column(
            "trust",
            existing_type=sa.String(length=16),
            existing_nullable=False,
            server_default=None,
        )
