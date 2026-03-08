from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routes.embed import router as embed_router
from app.service.embedder import HFEmbedder
from app.service.inference_service import InferenceService


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedder = HFEmbedder(settings.model_name)
    app.state.inference_service = InferenceService(embedder)
    yield


app = FastAPI(title="Embeddings Service", lifespan=lifespan)
app.include_router(embed_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
