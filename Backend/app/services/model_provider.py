from dataclasses import dataclass, field
from typing import Any, Sequence

from app.model import get_model
from app.services.moderation import ModelPredictionError, ModelUnavailableError


@dataclass
class ModerationModelProvider:
    _model: Any | None = field(default=None, init=False, repr=False)

    def load(self) -> None:
        self._model = get_model()

    def predict_proba(self, features: Sequence[float]) -> float:
        if self._model is None:
            raise ModelUnavailableError("moderation model is not loaded")

        try:
            probability = float(self._model.predict_proba([list(features)])[0][1])
        except Exception as exc:
            raise ModelPredictionError("predictions are unavailable") from exc

        return probability
