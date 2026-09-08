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
MEMORY_TYPE_NOTE = "note"
MEMORY_EMBEDDING_DIMENSIONS = 768


class UserMemory(Base):
    """A durable fact or note remembered for one authenticated user.

    Two tiers, because they need different policies rather than because the data
    differs:

    - Facts are a fixed set of profile fields keyed by ``memory_key`` (name,
      location, occupation, preferences, ...), one row per key per user, pinned
      into every prompt. Their value is the user's own short free text, sanitized
      before storage.
    - Notes carry longer free text under a closed ``category``, found by semantic
      search rather than pinned, and expiry-checked so lapsed context stops
      reaching prompts.

    Every record carries its embedding, so both tiers share one retrieval shape.
    """

    __tablename__ = "user_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('fact', 'note')",
            name="ck_user_memories_type",
        ),
        CheckConstraint(
            "memory_type != 'fact' OR "
            "(memory_key IS NOT NULL AND length(btrim(memory_key)) > 0)",
            name="ck_user_memories_fact_key",
        ),
        CheckConstraint(
            "memory_type != 'note' OR "
            "(category IS NOT NULL AND length(btrim(category)) > 0)",
            name="ck_user_memories_note_category",
        ),
        CheckConstraint(
            "memory_type = 'note' OR category IS NULL",
            name="ck_user_memories_non_note_category",
        ),
        CheckConstraint(
            "memory_type = 'note' OR event_at IS NULL",
            name="ck_user_memories_non_note_event_at",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > created_at",
            name="ck_user_memories_valid_until",
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
        # Note retrieval always filters owner, active, type and expiry together.
        Index(
            "ix_user_memories_owner_active_notes",
            "user_id",
            "is_active",
            "memory_type",
            "valid_until",
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
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    """Closed routing dimension for notes; null for facts.

    Deliberately the only closed part of a note. It decides expiry horizon and
    how the memory is presented, so it has to stay small enough for a small model
    to classify consistently.
    """

    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    """Short label for what a note is about. Display and debugging only.

    Not an identity: the extractor cannot be relied on to phrase the same subject
    identically across turns, so deduplication uses embeddings instead.
    """

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
    event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """When the remembered thing happens; null when it has no date.

    Distinct from ``valid_until``, which is when the memory stops being used. A trip
    in March has an event date in March and stays useful for a while afterwards.
    Most notes have neither.

    Deliberately unconstrained. A date in the past is legitimate — the user may
    mention something that already happened — and rejecting that at the schema level
    would turn a harmless case into a lost memory.
    """

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """When this memory stops being usable; null means it never expires.

    Retrieval filters on it directly rather than relying on a sweep, so an
    expired memory stops reaching prompts the moment it lapses. Only notes set
    it: a preference has no natural end, but a plan or an event does, and without
    an end date stale context keeps being asserted as current.
    """

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
