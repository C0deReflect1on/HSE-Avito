from fastapi import APIRouter, HTTPException

from app.repositories.moderation_repository import repository
from app.repositories.items import ItemRepository
from app.schemas import PredictRequest, SimplePredictRequest
from app.services.model_provider import ModerationModelProvider
from app.services.moderation import AlwaysAvailableService, ModerationService


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
