from dataclasses import dataclass, field
from typing import Any, Protocol

import asyncpg
from app.schemas import PredictRequest, PredictResponse
from app.exceptions import WrongItemIdError
from app.storage.memory import InMemoryStorage
from app.db import get_pool
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PredictionCacheStorage(Protocol):
    async def get_prediction(self, cache_key: str) -> PredictResponse | None: ...
    async def set_prediction(self, cache_key: str, response: PredictResponse) -> None: ...
    async def delete_prediction(self, cache_key: str) -> None: ...


@dataclass
class _CacheRef:
    storage: PredictionCacheStorage | None = None


@dataclass(frozen=True)
class ModerationRepository:
    _storage: InMemoryStorage
    _cache_ref: _CacheRef = field(default_factory=_CacheRef)

    # кажется это уже deprecated просто
    def save_prediction(self, payload: PredictRequest, result: bool) -> None:
        self._storage.add_prediction(payload, result)

    def configure_cache_storage(self, cache_storage: PredictionCacheStorage) -> None:
        self._cache_ref.storage = cache_storage

    async def get_cached_prediction(self, cache_key: str) -> PredictResponse | None:
        if self._cache_ref.storage is None:
            return None
        return await self._cache_ref.storage.get_prediction(cache_key)

    async def cache_prediction(self, cache_key: str, response: PredictResponse) -> None:
        if self._cache_ref.storage is None:
            return None
        await self._cache_ref.storage.set_prediction(cache_key, response)

    async def delete_cached_prediction(self, cache_key: str) -> None:
        if self._cache_ref.storage is None:
            return None
        await self._cache_ref.storage.delete_prediction(cache_key)
    
    async def create_pending(self, payload: PredictRequest) -> int:
        pool = get_pool()
        try:
            task_id = await pool.fetchval(
                """
                INSERT INTO moderation_results (item_id, status)
                VALUES ($1, 'pending')
                RETURNING id
                """,
                payload.item_id,
            )
            return int(task_id)
        except asyncpg.exceptions.ForeignKeyViolationError:
            raise WrongItemIdError()

    async def get_by_id(self, task_id: int) -> dict[str, Any] | None:
        logger.info("in get_by_id: %s", task_id)
        pool = get_pool()
        row = await pool.fetchrow(
            """
            SELECT
                id,
                item_id,
                status,
                is_violation,
                probability,
                error_message,
                created_at,
                processed_at
            FROM moderation_results
            WHERE id = $1
            """,
            task_id,
        )
        return dict(row) if row is not None else None
    
    async def update_completed(self, task_id: int, is_violation: bool, probability: float) -> None:
        pool = get_pool()
        await pool.execute(
            """
            UPDATE moderation_results
            SET status = 'completed', is_violation = $2, probability = $3, processed_at = NOW()
            WHERE id = $1
            """,
            task_id, is_violation, probability)
    
    async def update_failed(self, task_id: int, error_message: str) -> None:
        pool = get_pool()
        await pool.execute(
            """
            UPDATE moderation_results
            SET status = 'failed', error_message = $2, processed_at = NOW()
            WHERE id = $1
            """,
            task_id, error_message)

    async def update_status(self, task_id: int, status: str, error: str | None = None) -> None:
        pool = get_pool()
        await pool.execute(
            """
            UPDATE moderation_results
            SET status = $2, error_message = $3, processed_at = NOW()
            WHERE id = $1
            """,
            task_id,
            status,
            error,
        )


storage = InMemoryStorage()
repository = ModerationRepository(storage)
