from fastapi import APIRouter

from app.repositories.moderation_repository import repository
from app.schemas import PredictRequest
from app.services.moderation import AlwaysAvailableService, ModerationService


router = APIRouter()

availability_checker = AlwaysAvailableService()
moderation_service = ModerationService(repository, availability_checker)


@router.post("/predict", response_model=bool)
def predict(payload: PredictRequest) -> bool:
    return moderation_service.predict(payload)
