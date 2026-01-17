from fastapi import APIRouter

from app.repositories.moderation_repository import repository
from app.schemas import PredictRequest
from app.services.moderation import ModerationService


router = APIRouter()

moderation_service = ModerationService(repository)


@router.post("/predict", response_model=bool)
def predict(payload: PredictRequest) -> bool:
    return moderation_service.predict(payload)
