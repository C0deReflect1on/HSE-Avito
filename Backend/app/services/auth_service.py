from datetime import datetime, timedelta, timezone

import jwt

from app.config import JWT_ALGORITHM, JWT_EXPIRATION_SECONDS, JWT_SECRET_KEY
from app.exceptions import AccountBlockedError, AuthenticationError, InvalidTokenError
from app.repositories.account_repository import AccountRepository
from app.schemas import Account
from app.services.password_hasher import hash_password


class AuthService:
    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    async def authenticate(self, login: str, password: str) -> Account:
        hashed_password = hash_password(password)
        account = await self.repository.get_by_credentials(login, hashed_password)
        if account is None:
            raise AuthenticationError("Invalid credentials")
        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return account

    def create_token(self, account: Account) -> str:
        payload = {
            "user_id": account.id,
            "login": account.login,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_EXPIRATION_SECONDS),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError("Invalid or expired token") from exc
