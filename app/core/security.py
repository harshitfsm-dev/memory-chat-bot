from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


class PasswordService:

    def __init__(self):
        self.password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify(
        self,
        password: str,
        hashed_password: str,
    ) -> bool:
        return self.password_hash.verify(
            password,
            hashed_password,
        )


class JWTService:

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        expire_minutes: int,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(
        self,
        user_id: str,
    ) -> str:

        expire = (
            datetime.now(timezone.utc)
            + timedelta(minutes=self.expire_minutes)
        )

        payload: dict[str, Any] = {
            "sub": user_id,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode_access_token(
        self,
        token: str,
    ) -> dict[str, Any]:

        return jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
        )