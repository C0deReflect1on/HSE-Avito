from fastapi import APIRouter

from app.repositories.moderation_repository import repository
from app.schemas import PredictRequest
from app.services.model_provider import ModerationModelProvider
from app.services.moderation import AlwaysAvailableService, ModerationService


router = APIRouter()

availability_checker = AlwaysAvailableService()
model_provider = ModerationModelProvider()
moderation_service = ModerationService(repository, availability_checker, model_provider)


@router.post("/predict", response_model=bool)
def predict(payload: PredictRequest) -> bool:
    return moderation_service.predict(payload)
