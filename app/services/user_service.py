from fastapi import HTTPException, status

from app.core.security import PasswordService
from app.models.user import User
from app.repositories.user_repository import (
    DuplicateUserEmailError,
    UserRepository,
)
from app.schemas.user import UserCreate


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        password_service: PasswordService,
    ):
        self.repository = repository
        self.password_service = password_service

    async def create_user(self, data: UserCreate) -> User:
        if await self.repository.get_by_email(data.email):
            raise self._email_conflict()

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=self.password_service.hash(data.password),
        )
        try:
            return await self.repository.create(user)
        except DuplicateUserEmailError as exc:
            raise self._email_conflict() from exc

    @staticmethod
    def _email_conflict() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
