"""Add pgvector-backed user long-term memory storage.

Revision ID: 20260907_0004
Revises: 20260906_0003
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import VECTOR
import sqlalchemy as sa


revision: str = "20260907_0004"
down_revision: str | Sequence[str] | None = "20260906_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 768


def upgrade() -> None:
    # The extension must exist before PostgreSQL can parse the VECTOR column.
    # The pgvector Docker image includes the extension files; this statement
    # enables it inside the application database.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "user_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("memory_type", sa.String(length=20), nullable=False),
        sa.Column("memory_key", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            VECTOR(EMBEDDING_DIMENSIONS),
            nullable=False,
        ),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "importance",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column("source_thread_id", sa.String(length=36), nullable=True),
        sa.Column("source_message_id", sa.String(length=36), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "memory_type IN ('fact', 'episode')",
            name="ck_user_memories_type",
        ),
        sa.CheckConstraint(
            "memory_type != 'fact' OR "
            "(memory_key IS NOT NULL AND length(btrim(memory_key)) > 0)",
            name="ck_user_memories_fact_key",
        ),
        sa.CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_user_memories_content",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_user_memories_confidence",
        ),
        sa.CheckConstraint(
            "importance >= 0 AND importance <= 1",
            name="ck_user_memories_importance",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_thread_id"],
            ["chat_threads.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "memory_type",
            "memory_key",
            name="uq_user_memories_owner_type_key",
        ),
    )
    op.create_index(
        "ix_user_memories_owner_active_type",
        "user_memories",
        ["user_id", "is_active", "memory_type"],
    )
    op.create_index(
        "ix_user_memories_embedding_hnsw",
        "user_memories",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_memories_embedding_hnsw",
        table_name="user_memories",
        postgresql_using="hnsw",
    )
    op.drop_index(
        "ix_user_memories_owner_active_type",
        table_name="user_memories",
    )
    op.drop_table("user_memories")

    # Do not drop the vector extension. It may have existed before this
    # migration or be used by another schema in the same database.
