import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from asyncpg.introspection import TypeRecord

from app import db
from app.repositories.items import ItemRepository
from app.repositories.moderation_repository import ModerationRepository
from app.storage.memory import InMemoryStorage
from app.services.model_provider import ModerationModelProvider
from app.services.moderation import AlwaysAvailableService, ModerationService
from app.schemas import PredictRequest
from app.settings import KAFKA_BOOTSTRAP, MODERATION_TOPIC, DLQ_TOPIC, CONSUMER_GROUP


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def main() -> None:
    await db.connect()

    model_provider = ModerationModelProvider()
    model_provider.load()

    # get rid of InMemoryStorage to db get pool()
    results_repo = ModerationRepository(InMemoryStorage())
    items_repo = ItemRepository()
    moderation_service = ModerationService(results_repo, AlwaysAvailableService(), model_provider)

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    dlq = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)

    await consumer.start()
    await dlq.start()

    logger.info("Worker started. Consuming topic=%s group=%s", MODERATION_TOPIC, CONSUMER_GROUP)

    try:
        async for msg in consumer:
            task_id = None
            item_id = None
            try:
                event = json.loads(msg.value.decode("utf-8"))
                task_id = int(event["task_id"])
                item_id = int(event["item_id"])

                item_data = await items_repo.get_item_with_user(item_id)
                if item_data is None:
                    raise RuntimeError(f"item not found: {item_id}")
                
                req = PredictRequest(
                    seller_id=item_data["seller_id"],
                    is_verified_seller=item_data["is_verified_seller"],
                    item_id=item_data["item_id"],
                    name=item_data["name"],
                    description=item_data["description"],
                    category=item_data["category"],
                    images_qty=item_data["images_qty"],
                )
                logger.info("before moderation_service.predict")
                is_violation = moderation_service.predict(req)

                await results_repo.update_completed(
                    task_id=task_id,
                    is_violation=is_violation,
                    probability=1.0 if is_violation else 0.0,
                )

                logger.info("after update_completed moderation_service.predict")
                await consumer.commit()

            except Exception as e:
                logger.info("in exception ", e)
                if task_id is not None:
                    await results_repo.update_failed(task_id, str(e))
                
                dlq_payload = {
                    "task_id": task_id,
                    "item_id": item_id,
                    "error": str(e),
                    "original": msg.value.decode("utf-8", errors="replace"),
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                }
                await dlq.send_and_wait(DLQ_TOPIC, json.dumps(dlq_payload).encode("utf-8"))

                await consumer.commit()
    finally:
        await consumer.stop()
        await dlq.stop()
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
