from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


class ChatMessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_messages(self, thread_id: str) -> list[ChatMessage]:
        """Every message in the thread, oldest first. Used by the UI."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.seq)
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        thread_id: str,
        limit: int,
        after_seq: int = 0,
    ) -> list[ChatMessage]:
        """The newest `limit` messages above `after_seq`, returned oldest first.

        This is what becomes the model's memory of the conversation.

        `after_seq` is the thread's summary boundary, so summarized messages are
        left out here and represented by the summary instead.

        The query sorts newest-first so the database can stop after `limit` rows,
        then the short list is reversed in Python to read chronologically.
        """
        if limit <= 0:
            return []

        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.thread_id == thread_id,
                ChatMessage.seq > after_seq,
            )
            .order_by(ChatMessage.seq.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def next_seq(self, thread_id: str) -> int:
        """The position the next message in this thread should get.

        Note: two requests writing to the same thread at the exact same moment
        could both read the same number. The unique constraint on
        (thread_id, seq) turns that into a clear error rather than silently
        mixed-up messages.
        """
        result = await self.db.execute(
            select(func.coalesce(func.max(ChatMessage.seq), 0)).where(
                ChatMessage.thread_id == thread_id
            )
        )
        return result.scalar_one() + 1

    def create(
        self,
        thread_id: str,
        role: str,
        content: str,
        seq: int,
    ) -> ChatMessage:
        """Stage a message. The caller commits through the unit of work.

        No flush: the INSERT is emitted with the surrounding commit, so a
        transcript turn costs one round trip instead of two.
        """
        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            seq=seq,
        )
        self.db.add(message)
        return message
