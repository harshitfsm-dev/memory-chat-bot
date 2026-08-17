from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
):

    repository = UserRepository(db)

    auth_service = AuthService(
        repository=repository,
        password_service=request.app.state.password_service,
        jwt_service=request.app.state.jwt_service,
    )

    token = await auth_service.login(
        email=data.email,
        password=data.password,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }