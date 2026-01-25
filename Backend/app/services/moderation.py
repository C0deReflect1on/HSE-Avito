from dataclasses import dataclass
import logging
from typing import Any, Protocol

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


@dataclass(frozen=True)
class AlwaysAvailableService:
    def ensure_available(self) -> None:
        return None


@dataclass(frozen=True)
class ModerationService:
    _repository: ModerationRepository
    _availability_checker: ServiceAvailability

    def _require_model(self, model: Any | None) -> Any:
        if model is None:
            raise ModelUnavailableError("moderation model is not loaded")
        return model

    def _prepare_features(self, payload: PredictRequest) -> dict[str, float]:
        return {
            "is_verified_seller": 1.0 if payload.is_verified_seller else 0.0,
            "images_qty": payload.images_qty / 10.0,
            "description_length": len(payload.description) / 1000.0,
            "category": payload.category / 100.0,
        }

    def predict(self, payload: PredictRequest, model: Any | None) -> bool:
        self._availability_checker.ensure_available()
        model = self._require_model(model)
        normalized_features = self._prepare_features(payload)
        feature_vector = list(normalized_features.values())

        try:
            probability = float(model.predict_proba([feature_vector])[0][1])
        except Exception as exc:
            raise ModelPredictionError("predictions are unavailable") from exc

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
