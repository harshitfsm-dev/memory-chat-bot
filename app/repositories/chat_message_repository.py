from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


class ChatMessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_messages(self, thread_id: str) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())

    def create(self, thread_id: str, role: str, content: str) -> ChatMessage:
        """Stage a message. The caller commits through the unit of work.

        No flush: the INSERT is emitted with the surrounding commit, so a
        transcript turn costs one round trip instead of two.
        """
        message = ChatMessage(thread_id=thread_id, role=role, content=content)
        self.db.add(message)
        return message
