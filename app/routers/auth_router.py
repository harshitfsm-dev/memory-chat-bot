from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    service = AuthService(
        repository=UserRepository(db),
        password_service=request.app.state.password_service,
        jwt_service=request.app.state.jwt_service,
    )
    token = await service.login(email=data.email, password=data.password)
    return TokenResponse(access_token=token)
