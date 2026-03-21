from dataclasses import dataclass

from app.db import get_pool
from app.utils.metrics import track_db_insert, track_db_select, track_db_update, track_db_delete
from app.schemas import Account


@dataclass(frozen=True)
class AccountRepository:
    async def create(self, login: str, hashed_password: str) -> Account:
        pool = get_pool()
        async with track_db_insert():
            row = await pool.fetchrow(
                """
                INSERT INTO account (login, password)
                VALUES ($1, $2)
                RETURNING id, login, is_blocked
                """,
                login,
                hashed_password,
            )
            return Account.model_validate(dict(row))

    async def get_by_id(self, account_id: int) -> Account | None:
        pool = get_pool()
        async with track_db_select():
            row = await pool.fetchrow(
                "SELECT id, login, is_blocked FROM account WHERE id = $1",
                account_id,
            )
            if row is None:
                return None
            return Account.model_validate(dict(row))

    async def get_by_login(self, login: str) -> Account | None:
        pool = get_pool()
        async with track_db_select():
            row = await pool.fetchrow(
                "SELECT id, login, is_blocked FROM account WHERE login = $1",
                login,
            )
            if row is None:
                return None
            return Account.model_validate(dict(row))

    async def get_by_credentials(self, login: str, hashed_password: str) -> Account | None:
        pool = get_pool()
        async with track_db_select():
            row = await pool.fetchrow(
                """
                SELECT id, login, is_blocked
                FROM account
                WHERE login = $1 AND password = $2
                """,
                login,
                hashed_password,
            )
            if row is None:
                return None
            return Account.model_validate(dict(row))

    async def block(self, account_id: int) -> bool:
        pool = get_pool()
        async with track_db_update():
            updated_id = await pool.fetchval(
                """
                UPDATE account
                SET is_blocked = TRUE
                WHERE id = $1
                RETURNING id
                """,
                account_id,
            )
            return updated_id is not None

    async def delete(self, account_id: int) -> bool:
        pool = get_pool()
        async with track_db_delete():
            deleted_id = await pool.fetchval(
                "DELETE FROM account WHERE id = $1 RETURNING id",
                account_id,
            )
            return deleted_id is not None
