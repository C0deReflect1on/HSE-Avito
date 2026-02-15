import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from fastapi.testclient import TestClient

from app.main import app

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _get_database_dsn() -> str | None:
    return os.getenv("TEST_DATABASE_DSN")


def _load_all_migrations_sql() -> str:
    migration_files = sorted(MIGRATION_PATH.glob("V*.sql"))
    parts = []
    for f in migration_files:
        parts.append(f.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


async def _execute_sql(dsn: str, sql: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def database_dsn() -> str:
    dsn = _get_database_dsn()
    if not dsn:
        raise RuntimeError("TEST_DATABASE_DSN is not set")
    return dsn


# @pytest.fixture(scope="session", autouse=True)
# def apply_migrations(database_dsn: str) -> None:
#     sql = _load_all_migrations_sql()
#     asyncio.run(_execute_sql(database_dsn, sql))
@pytest.fixture(scope="session", autouse=True)
def apply_migrations(database_dsn: str) -> None:
    async def setup():
        conn = await asyncpg.connect(database_dsn)
        try:
            await conn.execute("DROP SCHEMA public CASCADE;")
            await conn.execute("CREATE SCHEMA public;")
        finally:
            await conn.close()

        sql = _load_all_migrations_sql()
        await _execute_sql(database_dsn, sql)

    asyncio.run(setup())



@pytest.fixture(autouse=True)
def truncate_tables(database_dsn: str) -> None:
    sql = "TRUNCATE moderation_results, items, users RESTART IDENTITY CASCADE;"
    asyncio.run(_execute_sql(database_dsn, sql))
    yield
    asyncio.run(_execute_sql(database_dsn, sql))


def _make_mock_kafka_producer():
    mock = MagicMock()
    mock.start = AsyncMock(return_value=None)
    mock.stop = AsyncMock(return_value=None)
    mock.send_moderation_request = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def client() -> TestClient:
    mock_producer = _make_mock_kafka_producer()
    with patch("app.main.KafkaProducer", return_value=mock_producer):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def client_with_kafka_mock():
    """Client + mock Kafka producer for asserting send_moderation_request calls."""
    mock_producer = _make_mock_kafka_producer()
    with patch("app.main.KafkaProducer", return_value=mock_producer):
        with TestClient(app) as client:
            yield client, mock_producer


@pytest.fixture
def payload_factory():
    def _factory(**overrides):
        payload = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 2,
            "images_qty": 2,
        }
        payload.update(overrides)
        return payload

    return _factory
