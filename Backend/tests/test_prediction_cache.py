import asyncio
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis

from app.repositories.moderation_repository import ModerationRepository
from app.schemas import PredictResponse
from app.storage.memory import InMemoryStorage
from app.storage.redis_cache import RedisPredictionCacheStorage


def test_repository_get_cached_prediction_calls_storage() -> None:
    async def _run() -> None:
        storage = AsyncMock()
        expected = PredictResponse(is_violation=True, probability=0.99)
        storage.get_prediction.return_value = expected
        repo = ModerationRepository(InMemoryStorage())
        repo.configure_cache_storage(storage)

        actual = await repo.get_cached_prediction("predict:key")

        assert actual == expected
        storage.get_prediction.assert_awaited_once_with("predict:key")

    asyncio.run(_run())


def test_repository_cache_prediction_calls_storage() -> None:
    async def _run() -> None:
        storage = AsyncMock()
        repo = ModerationRepository(InMemoryStorage())
        repo.configure_cache_storage(storage)
        response = PredictResponse(is_violation=False, probability=0.2)

        await repo.cache_prediction("predict:key", response)

        storage.set_prediction.assert_awaited_once_with("predict:key", response)

    asyncio.run(_run())


def test_repository_cache_methods_without_storage_do_not_fail() -> None:
    async def _run() -> None:
        repo = ModerationRepository(InMemoryStorage())
        response = PredictResponse(is_violation=False, probability=0.3)

        actual = await repo.get_cached_prediction("missing:key")
        await repo.cache_prediction("missing:key", response)

        assert actual is None

    asyncio.run(_run())


@pytest.mark.integration
def test_redis_prediction_cache_roundtrip() -> None:
    async def _run() -> None:
        redis_url = "redis://localhost:6379/15"
        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            await client.ping()
        except Exception as exc:
            await client.aclose()
            pytest.skip(f"Redis is unavailable for integration test: {exc}")

        storage = RedisPredictionCacheStorage(client, ttl_seconds=30)
        key = "predict:test:roundtrip"
        expected = PredictResponse(is_violation=True, probability=0.81)

        try:
            await client.delete(key)
            await storage.set_prediction(key, expected)
            actual = await storage.get_prediction(key)
            assert actual == expected
        finally:
            await client.delete(key)
            await client.aclose()

    asyncio.run(_run())


@pytest.mark.integration
def test_redis_prediction_cache_ttl_expiration() -> None:
    async def _run() -> None:
        redis_url = "redis://localhost:6379/15"
        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            await client.ping()
        except Exception as exc:
            await client.aclose()
            pytest.skip(f"Redis is unavailable for integration test: {exc}")

        storage = RedisPredictionCacheStorage(client, ttl_seconds=1)
        key = "predict:test:ttl"

        try:
            await client.delete(key)
            await storage.set_prediction(
                key, PredictResponse(is_violation=False, probability=0.13)
            )
            assert await storage.get_prediction(key) is not None
            await asyncio.sleep(1.2)
            assert await storage.get_prediction(key) is None
        finally:
            await client.delete(key)
            await client.aclose()

    asyncio.run(_run())
