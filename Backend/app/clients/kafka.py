import json
from aiokafka import AIOKafkaProducer


class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap)
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None  # чтобы не использовать после stop

    async def send_moderation_request(self, topic: str, task_id: int, item_id: int) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")

        data = json.dumps({"task_id": task_id, "item_id": item_id}).encode("utf-8")
        await self._producer.send_and_wait(topic, data)
