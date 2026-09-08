"""Record when a remembered thing actually happens, separately from its expiry.

Phase 2 gave notes a per-category lifetime, which fixed the worst failure — a
finished trip asserted as upcoming forever — but only coarsely. Every plan lapsed
90 days after it was mentioned, whether the trip was next week or next year.

`event_at` is the thing itself: the date the trip starts, the launch happens, the
deadline falls. `valid_until` stays what it always was, the point after which the
memory stops being used, and is now derived from `event_at` plus a grace period
when one is known. Two columns rather than one because they answer different
questions and only one of them is ever known for certain.

Nullable and unconstrained on purpose. Most notes have no date at all, and a note
about something already past is legitimate — it just must not drag `valid_until`
back before `created_at`, which the service clamps rather than the schema forbids.

Revision ID: 20260908_0007
Revises: 20260908_0006
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260908_0007"
down_revision: str | Sequence[str] | None = "20260908_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_memories",
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_memories_non_note_event_at",
        "user_memories",
        "memory_type = 'note' OR event_at IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_memories_non_note_event_at", "user_memories", type_="check"
    )
    op.drop_column("user_memories", "event_at")
