from dataclasses import dataclass

from app.repositories.moderation_repository import ModerationRepository
from app.schemas import PredictRequest


class ModerationError(Exception):
    pass


@dataclass
class ModerationService:
    _repository: ModerationRepository
    service_up: bool = True

    def predict(self, payload: PredictRequest) -> bool:
        self._ensure_service_is_available()
        if payload.is_verified_seller:
            result = True
        else:
            result = payload.images_qty > 0
        self._repository.save_prediction(payload, result)
        return result

    def _ensure_service_is_available(self) -> None:
        if not self.service_up:
            raise ModerationError("service temporarily unavailable")
