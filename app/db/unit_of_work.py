import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.errors import PersistenceError

logger = logging.getLogger(__name__)


class UnitOfWork:
    """Owns the transaction boundary for a request.

    Repositories only stage work on the session; deciding when that work
    becomes durable belongs to the service that understands the operation.

    Committing is also what returns the pooled connection, so services that
    perform slow non-database work (model inference) must commit before it and
    open a fresh transaction afterwards. Wrapping a whole request in one
    transaction would pin a connection for the duration of that work.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def commit(self) -> None:
        """Make staged work durable and release the pooled connection."""
        try:
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            logger.exception("Commit failed; transaction rolled back")
            raise PersistenceError("Could not commit the transaction") from exc

    async def rollback(self) -> None:
        await self._session.rollback()


def get_unit_of_work(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWork:
    return UnitOfWork(db)
