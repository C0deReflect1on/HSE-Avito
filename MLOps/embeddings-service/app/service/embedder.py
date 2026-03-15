from typing import Protocol, runtime_checkable

from sentence_transformers import SentenceTransformer


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode input texts into embeddings."""


class HFEmbedder:
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=max(1, min(len(texts), 32)),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()
