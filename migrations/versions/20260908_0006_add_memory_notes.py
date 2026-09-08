"""Add an open-vocabulary 'note' memory tier alongside facts and episodes.

Facts and episodes can only describe what the canonical vocabulary already
covers, so anything outside it — a travel plan, a personal goal, an upcoming
event — was silently dropped. Notes keep a small closed `category` for policy
decisions but carry free-text content, which is what makes them general.

`memory_key` stays null for notes, so they accumulate like episodes rather than
colliding on the owner/type/key unique constraint (PostgreSQL treats nulls as
distinct). Deduplication is by embedding similarity instead, which tolerates the
extractor phrasing the same thing differently on different turns.

`valid_until` exists because most note-worthy context is not permanent. Without
it, "flying to Tokyo next month" would still be injected into prompts a year
later, which is worse than never having stored it.

Revision ID: 20260908_0006
Revises: 20260907_0005
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260908_0006"
down_revision: str | Sequence[str] | None = "20260907_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_memories",
        sa.Column("category", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_memories",
        sa.Column("subject", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "user_memories",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Widen the type check rather than replace the concept: facts and episodes
    # keep their existing meaning and their closed vocabulary untouched.
    op.drop_constraint("ck_user_memories_type", "user_memories", type_="check")
    op.create_check_constraint(
        "ck_user_memories_type",
        "user_memories",
        "memory_type IN ('fact', 'episode', 'note')",
    )

    # `category` is what makes a note routable: it decides pinning, expiry and
    # display. A note without one cannot be governed, so the database refuses it.
    op.create_check_constraint(
        "ck_user_memories_note_category",
        "user_memories",
        "memory_type != 'note' OR "
        "(category IS NOT NULL AND length(btrim(category)) > 0)",
    )
    # The reverse, so a stray category cannot make a fact or episode look like a
    # note to any query that filters on it.
    op.create_check_constraint(
        "ck_user_memories_non_note_category",
        "user_memories",
        "memory_type = 'note' OR category IS NULL",
    )
    op.create_check_constraint(
        "ck_user_memories_valid_until",
        "user_memories",
        "valid_until IS NULL OR valid_until > created_at",
    )

    # Note retrieval always filters owner, active, type and expiry together.
    op.create_index(
        "ix_user_memories_owner_active_notes",
        "user_memories",
        ["user_id", "is_active", "memory_type", "valid_until"],
    )

    # No backfill: existing facts and episodes want category NULL, which is
    # exactly what add_column gives them and what the new checks require.


def downgrade() -> None:
    op.drop_index(
        "ix_user_memories_owner_active_notes",
        table_name="user_memories",
    )
    op.drop_constraint(
        "ck_user_memories_valid_until", "user_memories", type_="check"
    )
    op.drop_constraint(
        "ck_user_memories_non_note_category", "user_memories", type_="check"
    )
    op.drop_constraint(
        "ck_user_memories_note_category", "user_memories", type_="check"
    )

    # Notes cannot survive a narrowed type check, and there is no fact or episode
    # shape that preserves their free-text content. Drop them explicitly rather
    # than letting the constraint fail on data this migration created.
    op.execute("DELETE FROM user_memories WHERE memory_type = 'note'")
    op.drop_constraint("ck_user_memories_type", "user_memories", type_="check")
    op.create_check_constraint(
        "ck_user_memories_type",
        "user_memories",
        "memory_type IN ('fact', 'episode')",
    )

    op.drop_column("user_memories", "valid_until")
    op.drop_column("user_memories", "subject")
    op.drop_column("user_memories", "category")
