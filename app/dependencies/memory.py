from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.unit_of_work import UnitOfWork, get_unit_of_work
from app.repositories.user_memory_repository import UserMemoryRepository
from app.services.user_memory_control_service import UserMemoryControlService


def get_user_memory_control_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserMemoryControlService:
    """Build a request-scoped service over the shared session and UoW."""
    return UserMemoryControlService(
        repository=UserMemoryRepository(db),
        uow=uow,
    )
