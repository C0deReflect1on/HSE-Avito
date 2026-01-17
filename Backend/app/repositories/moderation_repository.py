from dataclasses import dataclass

from app.schemas import PredictRequest
from app.storage.memory import InMemoryStorage


@dataclass(frozen=True)
class ModerationRepository:
    _storage: InMemoryStorage

    def save_prediction(self, payload: PredictRequest, result: bool) -> None:
        self._storage.add_prediction(payload, result)


storage = InMemoryStorage()
repository = ModerationRepository(storage)
