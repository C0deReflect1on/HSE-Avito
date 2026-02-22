import json

from redis.asyncio import Redis

from app.schemas import PredictResponse


class RedisPredictionCacheStorage:
    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis = redis_client
        # 15 minutes keeps responses hot for repeated checks,
        # but is short enough to reduce stale decisions after item changes.
        self._ttl_seconds = ttl_seconds

    async def get_prediction(self, cache_key: str) -> PredictResponse | None:
        raw_value = await self._redis.get(cache_key)
        if raw_value is None:
            return None
        await self._redis.expire(cache_key, self._ttl_seconds)
        payload = json.loads(raw_value)
        return PredictResponse(**payload)

    async def set_prediction(self, cache_key: str, response: PredictResponse) -> None:
        await self._redis.set(
            name=cache_key,
            value=response.model_dump_json(),
            ex=self._ttl_seconds,
        )

    async def delete_prediction(self, cache_key: str) -> None:
        await self._redis.delete(cache_key)
