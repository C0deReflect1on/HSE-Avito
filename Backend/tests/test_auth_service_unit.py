import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest

from app.config import JWT_ALGORITHM, JWT_EXPIRATION_SECONDS, JWT_SECRET_KEY
from app.exceptions import AccountBlockedError, AuthenticationError, InvalidTokenError
from app.schemas import Account
from app.services.auth_service import AuthService
from app.services.password_hasher import hash_password

pytestmark = pytest.mark.unit


def test_authenticate_success():
    repository = AsyncMock()
    repository.get_by_credentials.return_value = Account(
        id=1, login="alice", is_blocked=False
    )
    service = AuthService(repository)

    account = asyncio.run(service.authenticate("alice", "password"))

    repository.get_by_credentials.assert_awaited_once_with("alice", hash_password("password"))
    assert account.id == 1


def test_authenticate_invalid_credentials():
    repository = AsyncMock()
    repository.get_by_credentials.return_value = None
    service = AuthService(repository)

    with pytest.raises(AuthenticationError):
        asyncio.run(service.authenticate("alice", "password"))


def test_authenticate_blocked_account():
    repository = AsyncMock()
    repository.get_by_credentials.return_value = Account(
        id=2, login="blocked", is_blocked=True
    )
    service = AuthService(repository)

    with pytest.raises(AccountBlockedError):
        asyncio.run(service.authenticate("blocked", "password"))


def test_create_token_contains_user_id():
    service = AuthService(AsyncMock())
    token = service.create_token(Account(id=9, login="user9", is_blocked=False))
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload["user_id"] == 9


def test_create_token_contains_exp():
    service = AuthService(AsyncMock())
    start = datetime.now(timezone.utc)
    token = service.create_token(Account(id=3, login="user3", is_blocked=False))
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected_min = start + timedelta(seconds=JWT_EXPIRATION_SECONDS - 2)
    expected_max = start + timedelta(seconds=JWT_EXPIRATION_SECONDS + 2)
    assert expected_min <= exp <= expected_max


def test_verify_token_valid():
    service = AuthService(AsyncMock())
    token = service.create_token(Account(id=4, login="ok", is_blocked=False))
    payload = service.verify_token(token)
    assert payload["user_id"] == 4
    assert payload["login"] == "ok"


def test_verify_token_expired():
    service = AuthService(AsyncMock())
    expired_token = jwt.encode(
        {"user_id": 1, "login": "x", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        service.verify_token(expired_token)


def test_verify_token_invalid_signature():
    service = AuthService(AsyncMock())
    wrong_token = jwt.encode(
        {"user_id": 1, "login": "x", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "another-secret",
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        service.verify_token(wrong_token)


def test_verify_token_malformed():
    service = AuthService(AsyncMock())
    with pytest.raises(InvalidTokenError):
        service.verify_token("not-a-jwt-token")
