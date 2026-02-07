import asyncio
from unittest.mock import patch

import asyncpg
import pytest

from app.routers import predict as predict_router
from app.services.moderation import (
    ModelPredictionError,
    ModelUnavailableError,
)


@pytest.mark.parametrize(
    "probability,payload_overrides,expected",
    [
        (0.8, {"is_verified_seller": False, "images_qty": 0}, True),
        (0.2, {"is_verified_seller": True, "images_qty": 2}, False),
    ],
)
def test_predict_probability_threshold(
    client,
    payload_factory,
    probability,
    payload_overrides,
    expected,
):
    with patch.object(
        predict_router.model_provider, "predict_proba", return_value=probability
    ):
        response = client.post("/predict", json=payload_factory(**payload_overrides))
    assert response.status_code == 200
    assert response.json() is expected


def test_predict_validation_error(client, payload_factory):
    payload = payload_factory(images_qty="invalid")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_simple_predict_validation_error(client):
    response = client.post("/simple_predict", json={"item_id": 0})
    assert response.status_code == 422


def test_predict_model_unavailable(client, payload_factory):
    with patch.object(
        predict_router.model_provider,
        "predict_proba",
        side_effect=ModelUnavailableError("moderation model is not loaded"),
    ):
        response = client.post("/predict", json=payload_factory())
    assert response.status_code == 503
    assert response.json()["detail"] == "moderation model is not loaded"


def test_predict_failure_returns_500(client, payload_factory):
    with patch.object(
        predict_router.model_provider,
        "predict_proba",
        side_effect=ModelPredictionError("predictions are unavailable"),
    ):
        response = client.post("/predict", json=payload_factory())
    assert response.status_code == 500
    assert response.json()["detail"] == "predictions are unavailable"


async def _seed_user_and_item(
    dsn: str,
    seller_id: int,
    is_verified: bool,
    item_id: int,
    name: str,
    description: str,
    category: int,
    images_qty: int,
) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(
            "INSERT INTO users (id, is_verified_seller) VALUES ($1, $2)",
            seller_id,
            is_verified,
        )
        await conn.execute(
            """
            INSERT INTO items (id, seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            item_id,
            seller_id,
            name,
            description,
            category,
            images_qty,
        )
    finally:
        await conn.close()


def test_simple_predict_positive(client, database_dsn):
    asyncio.run(
        _seed_user_and_item(
            database_dsn,
            seller_id=11,
            is_verified=False,
            item_id=101,
            name="Item",
            description="Description",
            category=2,
            images_qty=1,
        )
    )
    with patch.object(
        predict_router.model_provider, "predict_proba", return_value=0.8
    ):
        response = client.post("/simple_predict", json={"item_id": 101})
    assert response.status_code == 200
    assert response.json() is True


def test_simple_predict_negative(client, database_dsn):
    asyncio.run(
        _seed_user_and_item(
            database_dsn,
            seller_id=12,
            is_verified=True,
            item_id=202,
            name="Item",
            description="Description",
            category=2,
            images_qty=2,
        )
    )
    with patch.object(
        predict_router.model_provider, "predict_proba", return_value=0.2
    ):
        response = client.post("/simple_predict", json={"item_id": 202})
    assert response.status_code == 200
    assert response.json() is False