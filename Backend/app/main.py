import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import predict as predict_router_module
from app.services.moderation import ModerationError, ModelUnavailableError, ModelPredictionError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(predict_router_module.router)


@app.on_event("startup")
def load_model() -> None:
    try:
        predict_router_module.model_provider.load()
    except Exception:
        logger.exception("Failed to load the moderation model")
        raise


@app.get("/")
async def root() -> dict:
    return {"message": "Hello World!"}


@app.exception_handler(ModerationError)
def handle_moderation_error(request: Request, exc: ModerationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(ModelPredictionError)
def handle_model_unavailable(request: Request, exc: ModelPredictionError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(ModelUnavailableError)
def handle_model_unavailable(request: Request, exc: ModelUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})
