"""Add the two columns short-term memory needs.

chat_messages.seq          position of a message inside its thread (1, 2, 3...)
chat_threads.summary_up_to_seq  how far the thread's summary already covers

Together they let us send the model: the summary of old messages, plus the
messages after that point, verbatim.

Revision ID: 20260906_0003
Revises: 20260901_0002
Create Date: 2026-09-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260906_0003"
down_revision: str | Sequence[str] | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added nullable first so existing rows can be filled in before the
    # NOT NULL constraint is applied.
    op.add_column("chat_messages", sa.Column("seq", sa.Integer(), nullable=True))

    # Number the existing messages within each thread, oldest first. `id` breaks
    # ties because messages saved together share a created_at value.
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY thread_id ORDER BY created_at, id
                   ) AS position
            FROM chat_messages
        )
        UPDATE chat_messages AS m
        SET seq = numbered.position
        FROM numbered
        WHERE m.id = numbered.id
        """
    )
    op.alter_column("chat_messages", "seq", nullable=False)

    # Two messages in one thread must never share a position.
    op.create_unique_constraint(
        "uq_chat_messages_thread_seq",
        "chat_messages",
        ["thread_id", "seq"],
    )

    # 0 means "nothing summarized yet", which is true for every existing thread.
    op.add_column(
        "chat_threads",
        sa.Column(
            "summary_up_to_seq",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_threads", "summary_up_to_seq")
    op.drop_constraint(
        "uq_chat_messages_thread_seq",
        "chat_messages",
        type_="unique",
    )
    op.drop_column("chat_messages", "seq")
