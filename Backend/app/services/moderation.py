from dataclasses import dataclass
import logging
from typing import Protocol

from app.repositories.moderation_repository import ModerationRepository
from app.schemas import PredictRequest


class ModerationError(Exception):
    pass


class ModelUnavailableError(ModerationError):
    pass


class ModelPredictionError(ModerationError):
    pass


class ServiceAvailability(Protocol):
    def ensure_available(self) -> None: ...


class ModelProvider(Protocol):
    def predict_proba(self, features: list[float]) -> float: ...


@dataclass(frozen=True)
class AlwaysAvailableService:
    def ensure_available(self) -> None:
        return None


@dataclass(frozen=True)
class ModerationService:
    _repository: ModerationRepository
    _availability_checker: ServiceAvailability
    _model_provider: ModelProvider

    def _prepare_features(self, payload: PredictRequest) -> dict[str, float]:
        return {
            "is_verified_seller": 1.0 if payload.is_verified_seller else 0.0,
            "images_qty": payload.images_qty / 10.0,
            "description_length": len(payload.description) / 1000.0,
            "category": payload.category / 100.0,
        }

    def predict(self, payload: PredictRequest) -> bool:
        self._availability_checker.ensure_available()
        normalized_features = self._prepare_features(payload)
        feature_vector = list(normalized_features.values())
        probability = self._model_provider.predict_proba(feature_vector)

        logger = logging.getLogger(__name__)
        logger.info(
            "Prediction request seller_id=%s item_id=%s features=%s",
            payload.seller_id,
            payload.item_id,
            normalized_features,
        )
        result = probability >= 0.5
        logger.info(
            "Prediction result seller_id=%s item_id=%s is_violation=%s probability=%.4f",
            payload.seller_id,
            payload.item_id,
            result,
            probability,
        )
        self._repository.save_prediction(payload, result)
        return result
