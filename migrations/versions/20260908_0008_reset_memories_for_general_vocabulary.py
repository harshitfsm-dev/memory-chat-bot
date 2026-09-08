"""Clear all stored memories after generalising the memory vocabulary.

The fact keys and canonical values stopped being programming-specific: the three
``current_technical_*`` keys were renamed to ``current_goal`` / ``current_project``
/ ``recurring_constraint``, and general-life keys (occupation, hobby, dietary
preference, spoken language, measurement system) were added.

Existing rows reference the old keys and the old technical framing, and they will
never be re-emitted under the new names, so they would linger as stale,
programming-framed context pinned into prompts. There is no automatic remapping
because the change is semantic, not mechanical — an old ``current_technical_goal``
row is not simply a ``current_goal`` row. The clean, predictable outcome is to
drop every memory and let it re-accumulate from new conversations under the new
vocabulary.

This deletes rows only from ``user_memories``. Users, threads and messages are
untouched. It is destructive in the sense that remembered context is lost, but it
is bounded to memory, which is derived data that rebuilds itself over subsequent
turns.

Revision ID: 20260908_0008
Revises: 20260908_0007
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260908_0008"
down_revision: str | Sequence[str] | None = "20260908_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A plain DELETE rather than TRUNCATE: user_memories is referenced by no other
    # table, but DELETE respects the same transaction Alembic wraps the migration
    # in and needs no extra privileges.
    op.execute("DELETE FROM user_memories")


def downgrade() -> None:
    # Deleted memories cannot be reconstructed — the source conversations were not
    # retained in this table — so there is nothing to restore. Downgrading the
    # schema is a no-op; the data loss is not reversible by design.
    pass
