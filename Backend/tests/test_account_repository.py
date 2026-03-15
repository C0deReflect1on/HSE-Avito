import asyncio

import asyncpg
import pytest

from app import db
from app.repositories.account_repository import AccountRepository
from app.services.password_hasher import hash_password

pytestmark = pytest.mark.integration


def test_create_account(database_dsn: str):
    async def _run():
        await db.connect(database_dsn)
        repo = AccountRepository()
        account = await repo.create("alice", hash_password("qwerty"))
        created = await repo.get_by_id(account.id)
        await db.disconnect()
        return account, created

    account, created = asyncio.run(_run())
    assert account.id > 0
    assert account.login == "alice"
    assert account.is_blocked is False
    assert created is not None
    assert created.id == account.id
    assert created.login == "alice"
    assert created.is_blocked is False

    # Проверяем именно состояние БД: пароль должен храниться как hash.
    async def _read_password():
        conn = await asyncpg.connect(database_dsn)
        try:
            return await conn.fetchval("SELECT password FROM account WHERE id = $1", account.id)
        finally:
            await conn.close()

    stored_password = asyncio.run(_read_password())
    assert stored_password == hash_password("qwerty")


def test_create_duplicate_login(database_dsn: str):
    async def _run():
        await db.connect(database_dsn)
        repo = AccountRepository()
        await repo.create("dupe", hash_password("one"))
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await repo.create("dupe", hash_password("two"))
        got = await repo.get_by_login("dupe")
        await db.disconnect()
        return got

    account = asyncio.run(_run())
    assert account is not None
    assert account.login == "dupe"


def test_get_by_id_found(database_dsn: str):
    async def _run():
        conn = await asyncpg.connect(database_dsn)
        try:
            account_id = await conn.fetchval(
                """
                INSERT INTO account (login, password, is_blocked)
                VALUES ($1, $2, FALSE)
                RETURNING id
                """,
                "bob",
                hash_password("pass"),
            )
        finally:
            await conn.close()

        await db.connect(database_dsn)
        repo = AccountRepository()
        got = await repo.get_by_id(int(account_id))
        await db.disconnect()
        return got

    account = asyncio.run(_run())
    assert account is not None
    assert account.login == "bob"


def test_get_by_id_not_found(database_dsn: str):
    async def _run():
        await db.connect(database_dsn)
        repo = AccountRepository()
        got = await repo.get_by_id(999_999)
        await db.disconnect()
        return got

    assert asyncio.run(_run()) is None


def test_get_by_login(database_dsn: str):
    async def _run():
        conn = await asyncpg.connect(database_dsn)
        try:
            await conn.execute(
                "INSERT INTO account (login, password) VALUES ($1, $2)",
                "john",
                hash_password("pass"),
            )
        finally:
            await conn.close()

        await db.connect(database_dsn)
        repo = AccountRepository()
        got = await repo.get_by_login("john")
        await db.disconnect()
        return got

    account = asyncio.run(_run())
    assert account is not None
    assert account.login == "john"


def test_get_by_credentials_valid(database_dsn: str):
    async def _run():
        conn = await asyncpg.connect(database_dsn)
        try:
            await conn.execute(
                "INSERT INTO account (login, password) VALUES ($1, $2)",
                "sam",
                hash_password("secret"),
            )
        finally:
            await conn.close()

        await db.connect(database_dsn)
        repo = AccountRepository()
        got = await repo.get_by_credentials("sam", hash_password("secret"))
        await db.disconnect()
        return got

    account = asyncio.run(_run())
    assert account is not None
    assert account.login == "sam"


def test_get_by_credentials_invalid(database_dsn: str):
    async def _run():
        conn = await asyncpg.connect(database_dsn)
        try:
            await conn.execute(
                "INSERT INTO account (login, password) VALUES ($1, $2)",
                "jane",
                hash_password("secret"),
            )
        finally:
            await conn.close()

        await db.connect(database_dsn)
        repo = AccountRepository()
        got = await repo.get_by_credentials("jane", hash_password("wrong"))
        await db.disconnect()
        return got

    assert asyncio.run(_run()) is None


def test_block_account(database_dsn: str):
    async def _run():
        await db.connect(database_dsn)
        repo = AccountRepository()
        created = await repo.create("blocked", hash_password("pass"))
        was_blocked = await repo.block(created.id)
        got = await repo.get_by_id(created.id)
        await db.disconnect()
        return was_blocked, got

    blocked, account = asyncio.run(_run())
    assert blocked is True
    assert account is not None
    assert account.is_blocked is True


def test_delete_account(database_dsn: str):
    async def _run():
        await db.connect(database_dsn)
        repo = AccountRepository()
        created = await repo.create("to-delete", hash_password("pass"))
        deleted = await repo.delete(created.id)
        got = await repo.get_by_id(created.id)
        await db.disconnect()
        return deleted, got

    deleted, account = asyncio.run(_run())
    assert deleted is True
    assert account is None
