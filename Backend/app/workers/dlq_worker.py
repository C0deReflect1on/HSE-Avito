import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app import db
from app.repositories.moderation_repository import ModerationRepository
from app.storage.memory import InMemoryStorage
from app.settings import KAFKA_BOOTSTRAP, MODERATION_TOPIC, DLQ_TOPIC

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAX_RETRIES = 3


async def main() -> None:
    await db.connect()

    results_repo = ModerationRepository(InMemoryStorage())

    consumer = AIOKafkaConsumer(
        DLQ_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="dlq_consumer_group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)

    await consumer.start()
    await producer.start()

    logger.info("DLQ worker started. Consuming topic=%s", DLQ_TOPIC)

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                task_id = payload.get("task_id")
                item_id = payload.get("item_id")
                retry_count = int(payload.get("retry_count", 0) or 0)
                error = payload.get("error", "unknown")

                if task_id is None or item_id is None:
                    logger.warning("DLQ message missing task_id or item_id: %s", payload)
                    await consumer.commit()
                    continue

                if retry_count >= MAX_RETRIES:
                    logger.info("Task %s failed %d times, marking as failed", task_id, retry_count)
                    await results_repo.update_failed(task_id, f"Failed after {MAX_RETRIES} retries: {error}")
                else:
                    retry_msg = {"task_id": task_id, "item_id": item_id, "retry_count": retry_count}
                    await producer.send_and_wait(
                        MODERATION_TOPIC,
                        json.dumps(retry_msg).encode("utf-8"),
                    )
                    logger.info("Retry %d/%d for task %s", retry_count, MAX_RETRIES, task_id)

                await consumer.commit()
            except Exception as e:
                logger.exception("DLQ processing failed: %s", e)
                # Don't commit - message will be reprocessed

    finally:
        await consumer.stop()
        await producer.stop()
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
