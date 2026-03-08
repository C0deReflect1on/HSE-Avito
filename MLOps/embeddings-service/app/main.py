from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routes.embed import router as embed_router
from app.service.embedder import HFEmbedder
from app.service.inference_service import InferenceService
from app.service.onnx_embedder import OnnxEmbedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend = settings.inference_backend.strip().lower()
    if backend == "onnx":
        embedder = OnnxEmbedder(
            model_name=settings.model_name,
            onnx_model_dir=settings.onnx_model_dir,
            provider=settings.onnx_execution_provider,
        )
    elif backend == "hf":
        embedder = HFEmbedder(settings.model_name)
    else:
        raise ValueError("INFERENCE_BACKEND must be either 'hf' or 'onnx'")

    app.state.inference_service = InferenceService(embedder)
    yield


app = FastAPI(title="Embeddings Service", lifespan=lifespan)
app.include_router(embed_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
