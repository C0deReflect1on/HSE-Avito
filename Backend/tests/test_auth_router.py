import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.password_hasher import hash_password

pytestmark = pytest.mark.integration


def _make_mock_kafka_producer():
    mock = MagicMock()
    mock.start = AsyncMock(return_value=None)
    mock.stop = AsyncMock(return_value=None)
    mock.send_moderation_request = AsyncMock(return_value=None)
    return mock


from conftest import db_connection


async def _insert_account(database_dsn: str, login: str, password: str, blocked: bool = False) -> None:
    async with db_connection(database_dsn) as conn:
        await conn.execute(
            """
            INSERT INTO account (login, password, is_blocked)
            VALUES ($1, $2, $3)
            """,
            login,
            hash_password(password),
            blocked,
        )


@pytest.fixture
def auth_client():
    mock_producer = _make_mock_kafka_producer()
    with patch("app.main.KafkaProducer", return_value=mock_producer), patch(
        "app.main.predict_router_module.model_provider.load", return_value=None
    ):
        with TestClient(app) as client:
            yield client


def test_login_success(auth_client: TestClient, database_dsn: str):
    asyncio.run(_insert_account(database_dsn, login="alice", password="secret"))
    response = auth_client.post("/login", json={"login": "alice", "password": "secret"})
    assert response.status_code == 200
    assert response.json()["message"] == "Authorized"
    assert response.cookies.get("access_token") is not None


def test_login_invalid_credentials(auth_client: TestClient, database_dsn: str):
    asyncio.run(_insert_account(database_dsn, login="bob", password="secret"))
    response = auth_client.post("/login", json={"login": "bob", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_blocked_account(auth_client: TestClient, database_dsn: str):
    asyncio.run(_insert_account(database_dsn, login="blocked", password="secret", blocked=True))
    response = auth_client.post("/login", json={"login": "blocked", "password": "secret"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Account is blocked"


def test_login_missing_fields(auth_client: TestClient):
    response = auth_client.post("/login", json={"login": "alice"})
    assert response.status_code == 422


def test_login_cookie_is_httponly(auth_client: TestClient, database_dsn: str):
    asyncio.run(_insert_account(database_dsn, login="charlie", password="secret"))
    response = auth_client.post("/login", json={"login": "charlie", "password": "secret"})
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
