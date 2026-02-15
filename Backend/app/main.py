import logging

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.clients.kafka import KafkaProducer
from app.routers import predict as predict_router_module
from app.routers import moderation_result as moderation_result_router_module
from app.services.moderation import (
    ModerationError,
    ModelUnavailableError,
    ModelPredictionError,
)

from .settings import KAFKA_BOOTSTRAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(predict_router_module.router)
app.include_router(moderation_result_router_module.router)


@app.on_event("startup")
async def startup() -> None:
    # DB + model
    try:
        await db.connect()
        predict_router_module.model_provider.load()
    except Exception:
        logger.exception("Failed to init DB or load the moderation model")
        raise

    # Kafka producer (single instance for whole app)
    try:
        producer = KafkaProducer(KAFKA_BOOTSTRAP)
        await producer.start()
        app.state.kafka_producer = producer
    except Exception:
        logger.exception("Failed to start the Kafka producer")
        raise


@app.on_event("shutdown")
async def shutdown() -> None:
    producer: KafkaProducer | None = getattr(app.state, "kafka_producer", None)
    if producer is not None:
        await producer.stop()
    await db.disconnect()


@app.get("/")
async def root() -> dict:
    return {"message": "Hello World!"}


@app.exception_handler(ModerationError)
def handle_moderation_error(request: Request, exc: ModerationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ModelPredictionError)
def handle_model_prediction_error(request: Request, exc: ModelPredictionError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(ModelUnavailableError)
def handle_model_unavailable(request: Request, exc: ModelUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(asyncpg.exceptions.UndefinedTableError)
def handle_missing_tables(request: Request, exc: asyncpg.PostgresError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "database schema is not initialized"},
    )
