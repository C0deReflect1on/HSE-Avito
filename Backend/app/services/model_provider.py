import os
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.model import get_model
from app.services.moderation import ModelPredictionError, ModelUnavailableError


@dataclass
class ModerationModelProvider:
    _model: Any | None = field(default=None, init=False, repr=False)

    def load(self) -> None:
        """Load model from local file or MLflow based on USE_MLFLOW env variable."""
        use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
        if use_mlflow:
            self._model = self._load_from_mlflow()
        else:
            self._model = get_model()

    def _load_from_mlflow(self) -> Any:
        """Load model from MLflow Model Registry."""
        try:
            import mlflow
            import mlflow.sklearn
        except ImportError as exc:
            raise ModelUnavailableError(
                "MLflow is not installed. Install with: pip install mlflow"
            ) from exc

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
        model_name = os.getenv("MLFLOW_MODEL_NAME", "moderation-model")
        stage = os.getenv("MLFLOW_MODEL_STAGE", "Production")

        try:
            mlflow.set_tracking_uri(tracking_uri)
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.sklearn.load_model(model_uri)
            return model
        except Exception as exc:
            raise ModelUnavailableError(
                f"Failed to load model from MLflow: {model_uri}"
            ) from exc

    def predict_proba(self, features: Sequence[float]) -> float:
        if self._model is None:
            raise ModelUnavailableError("moderation model is not loaded")

        try:
            probability = float(self._model.predict_proba([list(features)])[0][1])
        except Exception as exc:
            raise ModelPredictionError("predictions are unavailable") from exc

        return probability
