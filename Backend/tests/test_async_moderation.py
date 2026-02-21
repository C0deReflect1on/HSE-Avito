"""Tests for async_predict, moderation_result, worker and DLQ."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from app.settings import DLQ_TOPIC, MODERATION_TOPIC


async def _seed_user_and_item(
    dsn: str,
    seller_id: int,
    is_verified: bool,
    item_id: int,
    name: str,
    description: str,
    category: int,
    images_qty: int,
) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(
            "INSERT INTO users (id, is_verified_seller) VALUES ($1, $2)",
            seller_id,
            is_verified,
        )
        await conn.execute(
            """
            INSERT INTO items (id, seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            item_id,
            seller_id,
            name,
            description,
            category,
            images_qty,
        )
    finally:
        await conn.close()


# --- async_predict tests ---


def test_async_predict_creates_task_and_sends_to_kafka(
    client_with_kafka_mock, database_dsn
):
    """POST /async_predict создаёт задачу в БД и отправляет сообщение в Kafka."""
    client, mock_producer = client_with_kafka_mock
    asyncio.run(
        _seed_user_and_item(
            database_dsn,
            seller_id=1,
            is_verified=False,
            item_id=100,
            name="Test item",
            description="Desc",
            category=5,
            images_qty=2,
        )
    )

    response = client.post("/async_predict", json={"item_id": 100})

    assert response.status_code == 200
    task_id = response.json()
    assert isinstance(task_id, int)
    assert task_id >= 1

    # Проверка вызова Kafka
    mock_producer.send_moderation_request.assert_called_once_with(
        MODERATION_TOPIC, task_id, 100
    )

    # Задача в БД со статусом pending
    moderation_response = client.get(f"/moderation_result/{task_id}")
    assert moderation_response.status_code == 200
    assert moderation_response.json()["status"] == "pending"
    assert moderation_response.json()["task_id"] == task_id




def test_async_predict_validation_error(client):
    """POST /async_predict с невалидным item_id возвращает 422."""
    response = client.post("/async_predict", json={"item_id": 0})
    assert response.status_code == 422


def test_async_predict_wrong_item_id(client):
    """POST /async_predict с несуществующим item_id возвращает 404 wrong_item_id."""
    # item_id=2 не создан в БД
    response = client.post("/async_predict", json={"item_id": 2})
    assert response.status_code == 404
    assert response.json()["detail"] == "wrong_item_id"


# --- moderation_result tests ---


def test_moderation_result_pending(client, database_dsn):
    """GET /moderation_result/{task_id} для задачи со статусом pending."""
    async def _create_pending_task():
        conn = await asyncpg.connect(database_dsn)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status)
                VALUES (NULL, 'pending')
                RETURNING id
                """
            )
            return row["id"]
        finally:
            await conn.close()

    task_id = asyncio.run(_create_pending_task())
    response = client.get(f"/moderation_result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert "result" not in data
    assert "error_message" not in data


def test_moderation_result_completed(client, database_dsn):
    """GET /moderation_result/{task_id} для задачи со статусом completed."""
    async def _create_completed_task():
        conn = await asyncpg.connect(database_dsn)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status, is_violation, probability)
                VALUES (NULL, 'completed', true, 0.85)
                RETURNING id
                """
            )
            return row["id"]
        finally:
            await conn.close()

    task_id = asyncio.run(_create_completed_task())
    response = client.get(f"/moderation_result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == {"is_violation": True, "probability": 0.85}


def test_moderation_result_failed(client, database_dsn):
    """GET /moderation_result/{task_id} для задачи со статусом failed."""
    async def _create_failed_task():
        conn = await asyncpg.connect(database_dsn)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status, error_message)
                VALUES (NULL, 'failed', 'item not found: 123')
                RETURNING id
                """
            )
            return row["id"]
        finally:
            await conn.close()

    task_id = asyncio.run(_create_failed_task())
    response = client.get(f"/moderation_result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "item not found: 123"


def test_moderation_result_not_found(client):
    """GET /moderation_result/{task_id} для несуществующей задачи — 404."""
    response = client.get("/moderation_result/999999")
    assert response.status_code == 404
    assert "task not found" in response.json()["detail"].lower()


# --- Worker message processing tests ---


class FakeMessage:
    """Имитация сообщения из Kafka."""
    def __init__(self, value: bytes, topic: str = "moderation", partition: int = 0, offset: int = 0):
        self.value = value
        self.topic = topic
        self.partition = partition
        self.offset = offset


class SimpleAsyncIterator:
    """Async iterator для имитации consumer."""
    def __init__(self, items):
        self.items = items
        self.i = 0
    def __aiter__(self):
        return self
    async def __anext__(self):
        if self.i >= len(self.items):
            raise StopAsyncIteration
        x = self.items[self.i]
        self.i += 1
        return x


def test_worker_processes_message_success(database_dsn):
    """Воркер обрабатывает сообщение: обновляет задачу на completed."""
    async def _run():
        await _seed_user_and_item(
            database_dsn,
            seller_id=1,
            is_verified=False,
            item_id=50,
            name="Item",
            description="Desc",
            category=3,
            images_qty=1,
        )

        conn = await asyncpg.connect(database_dsn)
        try:
            task_id = await conn.fetchval(
                "INSERT INTO moderation_results (item_id, status) VALUES (50, 'pending') RETURNING id"
            )
        finally:
            await conn.close()

        msg = FakeMessage(json.dumps({"task_id": task_id, "item_id": 50}).encode("utf-8"))

        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock(return_value=None)
        mock_consumer.stop = AsyncMock(return_value=None)
        mock_consumer.commit = AsyncMock(return_value=None)
        mock_consumer.__aiter__ = lambda: SimpleAsyncIterator([msg])

        mock_dlq = MagicMock()
        mock_dlq.start = AsyncMock(return_value=None)
        mock_dlq.stop = AsyncMock(return_value=None)
        mock_dlq.send_and_wait = AsyncMock(return_value=None)

        with patch("app.workers.moderation_worker.AIOKafkaConsumer", return_value=mock_consumer), \
             patch("app.workers.moderation_worker.AIOKafkaProducer", return_value=mock_dlq), \
             patch(
                 "app.workers.moderation_worker.ModerationModelProvider"
             ) as MockProvider:
            mock_prov = MagicMock()
            mock_prov.load = MagicMock()
            mock_prov.predict_proba = MagicMock(return_value=0.8)
            MockProvider.return_value = mock_prov

            from app.workers.moderation_worker import main
            await main()

        # Проверка: задача обновлена на completed
        conn = await asyncpg.connect(database_dsn)
        try:
            row = await conn.fetchrow(
                "SELECT status, is_violation FROM moderation_results WHERE id = $1",
                task_id,
            )
            assert row is not None
            assert row["status"] == "completed"
            assert row["is_violation"] is True
        finally:
            await conn.close()

        return mock_dlq

    mock_dlq = asyncio.run(_run())
    # DLQ не вызывался (ошибок не было)
    mock_dlq.send_and_wait.assert_not_called()


def test_worker_sends_to_dlq_on_error(database_dsn):
    """При ошибке воркер отправляет сообщение в DLQ."""
    async def _run():
        msg = FakeMessage(json.dumps({"task_id": 1, "item_id": 99999}).encode("utf-8"))

        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock(return_value=None)
        mock_consumer.stop = AsyncMock(return_value=None)
        mock_consumer.commit = AsyncMock(return_value=None)
        mock_consumer.__aiter__ = lambda: SimpleAsyncIterator([msg])

        mock_dlq = MagicMock()
        mock_dlq.start = AsyncMock(return_value=None)
        mock_dlq.stop = AsyncMock(return_value=None)
        mock_dlq.send_and_wait = AsyncMock(return_value=None)

        with patch("app.workers.moderation_worker.AIOKafkaConsumer", return_value=mock_consumer), \
             patch("app.workers.moderation_worker.AIOKafkaProducer", return_value=mock_dlq):
            from app.workers.moderation_worker import main
            await main()

        return mock_dlq

    mock_dlq = asyncio.run(_run())

    # DLQ вызван с корректным payload
    mock_dlq.send_and_wait.assert_called_once()
    call_args = mock_dlq.send_and_wait.call_args
    assert call_args[0][0] == DLQ_TOPIC
    dlq_body = json.loads(call_args[0][1].decode("utf-8"))
    assert dlq_body["task_id"] == 1
    assert dlq_body["item_id"] == 99999
    assert dlq_body["retry_count"] == 1
    assert "item not found" in dlq_body["error"]
    assert "original" in dlq_body


def test_dlq_worker_marks_failed_after_3_retries(database_dsn):
    """DLQ consumer при retry_count >= 3 помечает задачу как failed, не шлёт retry."""
    async def _run():
        await _seed_user_and_item(
            database_dsn,
            seller_id=1,
            is_verified=False,
            item_id=99,
            name="Item",
            description="Desc",
            category=1,
            images_qty=0,
        )
        conn = await asyncpg.connect(database_dsn)
        try:
            task_id = await conn.fetchval(
                "INSERT INTO moderation_results (item_id, status) VALUES (99, 'pending') RETURNING id"
            )
        finally:
            await conn.close()

        msg = FakeMessage(
            json.dumps({
                "task_id": task_id,
                "item_id": 99,
                "retry_count": 3,
                "error": "item not found",
                "original": "{}",
            }).encode("utf-8")
        )

        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock(return_value=None)
        mock_consumer.stop = AsyncMock(return_value=None)
        mock_consumer.commit = AsyncMock(return_value=None)
        mock_consumer.__aiter__ = lambda: SimpleAsyncIterator([msg])

        mock_producer = MagicMock()
        mock_producer.start = AsyncMock(return_value=None)
        mock_producer.stop = AsyncMock(return_value=None)
        mock_producer.send_and_wait = AsyncMock(return_value=None)

        with patch("app.workers.dlq_worker.AIOKafkaConsumer", return_value=mock_consumer), \
             patch("app.workers.dlq_worker.AIOKafkaProducer", return_value=mock_producer):
            from app.workers.dlq_worker import main
            await main()

        # Retry не должен вызываться (retry_count >= 3)
        mock_producer.send_and_wait.assert_not_called()

        # Статус должен быть failed
        conn = await asyncpg.connect(database_dsn)
        try:
            row = await conn.fetchrow(
                "SELECT status, error_message FROM moderation_results WHERE id = $1",
                task_id,
            )
            assert row is not None
            assert row["status"] == "failed"
            assert "3 retries" in row["error_message"]
        finally:
            await conn.close()

    asyncio.run(_run())


def test_dlq_worker_retries_when_count_less_than_3():
    """DLQ consumer при retry_count < 3 переотправляет в MODERATION_TOPIC."""
    async def _run():
        msg = FakeMessage(
            json.dumps({
                "task_id": 1,
                "item_id": 100,
                "retry_count": 1,
                "error": "item not found",
                "original": "{}",
            }).encode("utf-8")
        )

        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock(return_value=None)
        mock_consumer.stop = AsyncMock(return_value=None)
        mock_consumer.commit = AsyncMock(return_value=None)
        mock_consumer.__aiter__ = lambda: SimpleAsyncIterator([msg])

        mock_producer = MagicMock()
        mock_producer.start = AsyncMock(return_value=None)
        mock_producer.stop = AsyncMock(return_value=None)
        mock_producer.send_and_wait = AsyncMock(return_value=None)

        with patch("app.workers.dlq_worker.AIOKafkaConsumer", return_value=mock_consumer), \
             patch("app.workers.dlq_worker.AIOKafkaProducer", return_value=mock_producer):
            from app.workers.dlq_worker import main
            await main()

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args[0][0] == MODERATION_TOPIC
        body = json.loads(call_args[0][1].decode("utf-8"))
        assert body["task_id"] == 1
        assert body["item_id"] == 100
        assert body["retry_count"] == 1

    asyncio.run(_run())
