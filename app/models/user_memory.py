from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid

MEMORY_TYPE_FACT = "fact"
MEMORY_TYPE_EPISODE = "episode"
MEMORY_EMBEDDING_DIMENSIONS = 768


class UserMemory(Base):
    """A durable fact or episode remembered for one authenticated user.

    Facts use a stable ``memory_key`` so later observations can replace them.
    Episodes leave the key empty and are stored as independent events. Every
    record carries its embedding so semantic retrieval can be added without
    changing the persistence shape.
    """

    __tablename__ = "user_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('fact', 'episode')",
            name="ck_user_memories_type",
        ),
        CheckConstraint(
            "memory_type != 'fact' OR "
            "(memory_key IS NOT NULL AND length(btrim(memory_key)) > 0)",
            name="ck_user_memories_fact_key",
        ),
        CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_user_memories_content",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_user_memories_confidence",
        ),
        CheckConstraint(
            "importance >= 0 AND importance <= 1",
            name="ck_user_memories_importance",
        ),
        UniqueConstraint(
            "user_id",
            "memory_type",
            "memory_key",
            name="uq_user_memories_owner_type_key",
        ),
        Index(
            "ix_user_memories_owner_active_type",
            "user_id",
            "is_active",
            "memory_type",
        ),
        Index(
            "ix_user_memories_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)
    memory_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(MEMORY_EMBEDDING_DIMENSIONS),
        nullable=False,
    )
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default="0.5",
    )
    source_thread_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_message_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
