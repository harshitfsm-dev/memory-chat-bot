"""Collapse long-term memory to two tiers and reset stored memories.

The memory model was simplified: episodes were removed, and the fact tier stopped
being a closed vocabulary. Facts are now a fixed set of free-text profile fields
(name, location, timezone, occupation, hobby, goal, preferences, ...); everything
else lives in notes.

At the database level the only structural change is the ``memory_type`` check,
which narrows from ``('fact', 'episode', 'note')`` to ``('fact', 'note')``. The
fact-key and note-category constraints already say what they need to; free-text
fact values need no new column because ``memory_key``/``content`` were never
vocabulary-constrained in the database.

All existing rows are dropped. Episode rows would violate the narrowed check, and
old fact rows were built from the retired closed vocabulary under the old keys and
would never be re-emitted — they would linger as stale pinned context. Clearing
memory and letting it re-accumulate under the new model is the clean, predictable
outcome. This touches ``user_memories`` only; users, threads and messages are
untouched.

Revision ID: 20260908_0009
Revises: 20260908_0008
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260908_0009"
down_revision: str | Sequence[str] | None = "20260908_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clear first so the narrowed check cannot fail on existing episode rows, and
    # so no stale, old-vocabulary fact survives into the new model.
    op.execute("DELETE FROM user_memories")

    op.drop_constraint("ck_user_memories_type", "user_memories", type_="check")
    op.create_check_constraint(
        "ck_user_memories_type",
        "user_memories",
        "memory_type IN ('fact', 'note')",
    )


def downgrade() -> None:
    # Widen the check back to include episodes. There is no data to restore — the
    # rows this migration cleared cannot be reconstructed — so the downgrade only
    # reopens the shape.
    op.drop_constraint("ck_user_memories_type", "user_memories", type_="check")
    op.create_check_constraint(
        "ck_user_memories_type",
        "user_memories",
        "memory_type IN ('fact', 'episode', 'note')",
    )
