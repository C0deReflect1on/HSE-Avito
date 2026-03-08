from time import perf_counter

from fastapi import APIRouter, HTTPException, Request

from app.schemas.embed import EmbedRequest, EmbedResponse
from app.service.inference_service import InferenceService

router = APIRouter()


@router.post("/embed", response_model=EmbedResponse)
def create_embeddings(payload: EmbedRequest, request: Request) -> EmbedResponse:
    if any(not text.strip() for text in payload.texts):
        raise HTTPException(status_code=422, detail="texts must not contain empty strings")

    service: InferenceService = request.app.state.inference_service
    started = perf_counter()
    embeddings = service.embed(payload.texts)
    elapsed_ms = (perf_counter() - started) * 1000

    return EmbedResponse(
        embeddings=embeddings,
        texts_count=len(payload.texts),
        inference_time_ms=round(elapsed_ms, 3),
    )
