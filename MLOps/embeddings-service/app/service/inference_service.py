from app.service.embedder import Embedder


class InferenceService:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embedder.embed(texts)
