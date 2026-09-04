from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class DuplicateUserEmailError(Exception):
    """Raised when a user's normalized email is already registered."""


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Stage a user and surface a duplicate email immediately.

        Unlike the chat repositories this flushes, because the unique index on
        `users.email` is only enforced once the INSERT reaches the database.
        Flushing here keeps that translation in the layer that knows about the
        constraint instead of leaking it into the caller's commit.

        The caller still owns the commit.
        """
        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            # Postgres aborts the transaction on a constraint violation, so it
            # cannot be reused. Roll back before handing control back.
            await self.db.rollback()
            raise DuplicateUserEmailError from exc

        return user
