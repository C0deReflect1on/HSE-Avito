import asyncio
import os
from pathlib import Path

import asyncpg
import pytest

from fastapi.testclient import TestClient

from app.main import app


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "V001__initial.sql"
)


def _get_database_dsn() -> str | None:
    return os.getenv("TEST_DATABASE_DSN")


def _load_migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").strip()


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


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(database_dsn: str) -> None:
    sql = _load_migration_sql()
    asyncio.run(_execute_sql(database_dsn, sql))


@pytest.fixture(autouse=True)
def truncate_tables(database_dsn: str) -> None:
    sql = "TRUNCATE items, users;"
    asyncio.run(_execute_sql(database_dsn, sql))
    yield
    asyncio.run(_execute_sql(database_dsn, sql))


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


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
