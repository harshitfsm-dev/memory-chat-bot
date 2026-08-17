from fastapi import HTTPException, status

from app.core.security import (
    JWTService,
    PasswordService,
)
from app.repositories.user_repository import UserRepository


class AuthService:

    def __init__(
        self,
        repository: UserRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
    ):
        self.repository = repository
        self.password_service = password_service
        self.jwt_service = jwt_service

    async def login(
        self,
        email: str,
        password: str,
    ) -> str:

        user = await self.repository.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not self.password_service.verify(
            password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        return self.jwt_service.create_access_token(
            user_id=str(user.id)
        )