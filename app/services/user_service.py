from fastapi import HTTPException, status

from app.core.security import PasswordService
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class UserService:

    def __init__(
        self,
        repository: UserRepository,
        password_service: PasswordService,
    ):
        self.repository = repository
        self.password_service = password_service

    async def create_user(
        self,
        data: UserCreate,
    ) -> User:

        existing_user = await self.repository.get_by_email(
            data.email
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=self.password_service.hash(
                data.password
            ),
        )

        return await self.repository.create(user)

    async def get_user(
        self,
        user_id,
    ) -> User:

        user = await self.repository.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user