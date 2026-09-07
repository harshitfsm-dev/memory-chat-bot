from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


# The two values stored in `role`. Kept here so the repository, the service and
# the memory helpers all use the same spelling.
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    # A thread cannot have two messages at the same position.
    __table_args__ = (
        UniqueConstraint("thread_id", "seq", name="uq_chat_messages_thread_seq"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_uuid,
    )

    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "chat_threads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    """Position of this message in its thread: 1, 2, 3...

    We order by this instead of `created_at` because messages saved in the same
    transaction get the same timestamp, which makes their order unpredictable.
    """

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    """Either ROLE_USER or ROLE_ASSISTANT."""

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )
