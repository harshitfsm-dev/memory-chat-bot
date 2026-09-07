"""Use write-time, timezone-aware chat message timestamps.

Memory deletion fences compare a source message's creation time with the
memory tombstone. PostgreSQL CURRENT_TIMESTAMP is fixed at transaction start,
and the original chat message column discarded timezone information. Normalize
the column and use clock_timestamp() so this comparison reflects row-write
order without timezone casts.

Revision ID: 20260907_0005
Revises: 20260907_0004
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260907_0005"
down_revision: str | Sequence[str] | None = "20260907_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "chat_messages",
        "created_at",
        existing_type=sa.DateTime(timezone=False),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("clock_timestamp()"),
        postgresql_using=(
            "created_at AT TIME ZONE current_setting('TimeZone')"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "chat_messages",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        postgresql_using=(
            "created_at AT TIME ZONE current_setting('TimeZone')"
        ),
    )
