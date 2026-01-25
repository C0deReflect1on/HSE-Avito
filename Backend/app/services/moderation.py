from dataclasses import dataclass
from typing import Protocol

from app.repositories.moderation_repository import ModerationRepository
from app.schemas import PredictRequest


class ModerationError(Exception):
    pass


class ServiceAvailability(Protocol):
    def ensure_available(self) -> None: ...


@dataclass(frozen=True)
class AlwaysAvailableService:
    def ensure_available(self) -> None:
        return None


@dataclass(frozen=True)
class ModerationService:
    _repository: ModerationRepository
    _availability_checker: ServiceAvailability

    def predict(self, payload: PredictRequest) -> bool:
        self._availability_checker.ensure_available()
        if payload.is_verified_seller:
            result = True
        else:
            result = payload.images_qty > 0
        self._repository.save_prediction(payload, result)
        return result
