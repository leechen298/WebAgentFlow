"""widen conversation_events.type to 64 chars

Revision ID: df9ed1494afd
Revises: a93d26f33594
Create Date: 2026-05-12 23:07:54.784369
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "df9ed1494afd"
down_revision = "a93d26f33594"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "conversation_events",
        "type",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "conversation_events",
        "type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
