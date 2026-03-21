import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.metrics import DB_QUERY_DURATION


@asynccontextmanager
async def track_db_query(query_type: str) -> AsyncIterator[None]:
    """
    Async context manager for tracking database query duration metrics.
    
    Usage:
        async with track_db_query("select"):
            result = await pool.fetchrow(...)
    
    Args:
        query_type: Type of query (select, insert, update, delete)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)


@asynccontextmanager
async def track_db_select() -> AsyncIterator[None]:
    """Shorthand for tracking SELECT queries."""
    async with track_db_query("select"):
        yield


@asynccontextmanager
async def track_db_insert() -> AsyncIterator[None]:
    """Shorthand for tracking INSERT queries."""
    async with track_db_query("insert"):
        yield


@asynccontextmanager
async def track_db_update() -> AsyncIterator[None]:
    """Shorthand for tracking UPDATE queries."""
    async with track_db_query("update"):
        yield


@asynccontextmanager
async def track_db_delete() -> AsyncIterator[None]:
    """Shorthand for tracking DELETE queries."""
    async with track_db_query("delete"):
        yield
