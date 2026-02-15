from fastapi import APIRouter, HTTPException
from fastapi import Depends
from app.deps import get_kafka_producer
from app.clients.kafka import KafkaProducer

from app.repositories.moderation_repository import repository
from app.repositories.items import ItemRepository
from app.schemas import PredictRequest, SimplePredictRequest
from app.exceptions import WrongItemIdError
from app.services.model_provider import ModerationModelProvider
from app.services.moderation import AlwaysAvailableService, ModerationService
from app.settings import MODERATION_TOPIC


router = APIRouter()
availability_checker = AlwaysAvailableService()
model_provider = ModerationModelProvider()
moderation_service = ModerationService(repository, availability_checker, model_provider)
item_repository = ItemRepository()


@router.post("/predict", response_model=bool)
def predict(payload: PredictRequest) -> bool:
    return moderation_service.predict(payload)


@router.post("/simple_predict", response_model=bool)
async def simple_predict(payload: SimplePredictRequest) -> bool:
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
async def async_predict(payload: SimplePredictRequest, producer: KafkaProducer = Depends(get_kafka_producer)):
    try:
        task_id = await repository.create_pending(payload)
    except WrongItemIdError:
        raise HTTPException(status_code=404, detail="wrong_item_id")
    await producer.send_moderation_request(MODERATION_TOPIC, task_id, payload.item_id)
    return task_id
