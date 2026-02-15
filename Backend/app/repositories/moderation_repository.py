from dataclasses import dataclass

import asyncpg
from app.schemas import PredictRequest
from app.exceptions import WrongItemIdError
from app.storage.memory import InMemoryStorage
from app.db import get_pool
from typing import Any
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass(frozen=True)
class ModerationRepository:
    _storage: InMemoryStorage

    # кажется это уже deprecated просто
    def save_prediction(self, payload: PredictRequest, result: bool) -> None:
        self._storage.add_prediction(payload, result)
    
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
        logger.info("in get_by_id:", task_id)
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


storage = InMemoryStorage()
repository = ModerationRepository(storage)
