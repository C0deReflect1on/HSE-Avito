from fastapi import APIRouter, HTTPException
from fastapi import Depends
from redis.asyncio import Redis
from app.deps import get_kafka_producer
from app.clients.kafka import KafkaProducer

from app.repositories.moderation_repository import repository
from app.repositories.items import ItemRepository
from app.schemas import (
    PredictRequest,
    SimplePredictRequest,
    AsyncPredictResponse,
    PredictResponse,
    CloseItemRequest,
)
from app.exceptions import WrongItemIdError
from app.services.model_provider import ModerationModelProvider
from app.services.moderation import AlwaysAvailableService, ModerationService
from app.settings import MODERATION_TOPIC
from app.settings import REDIS_URL


router = APIRouter()
availability_checker = AlwaysAvailableService()
model_provider = ModerationModelProvider()
moderation_service = ModerationService(repository, availability_checker, model_provider)
item_repository = ItemRepository()


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    return moderation_service.predict(payload)


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(payload: SimplePredictRequest) -> PredictResponse:
    item_data = await item_repository.get_item_with_user(payload.item_id)
    if item_data is None:
        raise HTTPException(status_code=404, detail="item not found")

    request_payload = PredictRequest(
        seller_id=item_data["seller_id"],
        is_verified_seller=item_data["is_verified_seller"],
        item_id=item_data["item_id"],
        name=item_data["name"],
        description=item_data["description"],
        category=item_data["category"],
        images_qty=item_data["images_qty"],
    )
    return moderation_service.predict(request_payload)


@router.post("/async_predict")
async def async_predict(
    payload: SimplePredictRequest,
    producer: KafkaProducer = Depends(get_kafka_producer)
) -> AsyncPredictResponse:
    task_id = None
    try:
        task_id = await repository.create_pending(payload)
        try:
            await producer.send_moderation_request(MODERATION_TOPIC, task_id, payload.item_id)
        except Exception as e:
            # Fail task if it Kafka failed
            await repository.update_status(task_id, "failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to send moderation request: {str(e)}")

        return {"task_id": task_id, "status": "pending", "message": "Moderation request accepted"}
    
    except WrongItemIdError:
        raise HTTPException(status_code=404, detail="wrong_item_id")


@router.post("/close")
async def close_item(payload: CloseItemRequest) -> dict[str, str]:
    deleted = await item_repository.close_item(payload.item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="item not found")

    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.delete(f"item_prediction:item_id:{payload.item_id}")
    finally:
        await redis.aclose()

    return {"status": "closed"}
