from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.unit_of_work import UnitOfWork, get_unit_of_work
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserResponse:
    service = UserService(
        repository=UserRepository(db),
        password_service=request.app.state.password_service,
        uow=uow,
    )
    return await service.create_user(data)
