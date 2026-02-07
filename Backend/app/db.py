import asyncio
import os
from typing import Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None
_pool_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_dsn() -> str:
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    if is_pytest:
        dsn = os.getenv("TEST_DATABASE_DSN")
        if not dsn:
            raise RuntimeError("TEST_DATABASE_DSN is not set")
        return dsn

    dsn = os.getenv("DATABASE_DSN")
    if not dsn:
        raise RuntimeError("DATABASE_DSN is not set")
    return dsn


async def connect(dsn: str | None = None) -> None:
    global _pool, _pool_loop
    loop = asyncio.get_running_loop()
    if _pool is not None and _pool_loop is loop:
        return
    if _pool is not None and _pool_loop is not loop:
        await _pool.close()
    _pool = await asyncpg.create_pool(dsn or _get_dsn())
    _pool_loop = loop


async def disconnect() -> None:
    global _pool, _pool_loop
    if _pool is None:
        return
    await _pool.close()
    _pool = None
    _pool_loop = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool
