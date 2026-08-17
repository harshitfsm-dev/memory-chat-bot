from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer()


class AuthDependency:

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(
            bearer_scheme
        ),
        db: AsyncSession = Depends(get_session),
    ) -> User:

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

        token = credentials.credentials

        try:
            jwt_service = request.app.state.jwt_service

            payload = jwt_service.decode_access_token(token)

            user_id = payload.get("sub")

            if not user_id:
                raise credentials_exception

        except InvalidTokenError:
            raise credentials_exception

        repository = UserRepository(db)

        user = await repository.get_by_id(user_id)

        if not user:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        return user
    

auth_dependency = AuthDependency()