from app.schemas import PredictRequest


class InMemoryStorage:
    def __init__(self) -> None:
        self.predictions: list[tuple[PredictRequest, bool]] = []

    def add_prediction(self, payload: PredictRequest, result: bool) -> None:
        self.predictions.append((payload, result))
