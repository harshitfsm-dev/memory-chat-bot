from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_thread import ChatThread


class ChatThreadRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_threads(self, user_id: str) -> list[ChatThread]:
        result = await self.db.execute(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, thread_id: str, user_id: str) -> ChatThread | None:
        """Fetch a thread only if it belongs to `user_id`.

        Thread ids arrive from the client, so ownership must be proven before
        loading or appending to a durable transcript.
        """
        result = await self.db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_id(self, thread_id: str, user_id: str) -> bool:
        """Stage a delete and report whether it matched an owned thread.

        The caller commits through the unit of work.
        """
        result = await self.db.execute(
            delete(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def create(self, user_id: str, title: str) -> ChatThread:
        """Stage a new thread and flush it. The caller still owns the commit.

        The flush is required, not incidental. Callers attach messages to this
        thread in the same transaction, and `chat_messages.thread_id` is a
        foreign key. There is no ORM `relationship` between the two models, so
        SQLAlchemy has no dependency information to order the inserts by and
        would otherwise emit the message before its thread.

        Flushing also populates the generated primary key. Both statements
        remain in one transaction, so they commit or roll back together.
        """
        thread = ChatThread(title=title, user_id=user_id)
        self.db.add(thread)
        await self.db.flush()
        return thread
