from unittest.mock import AsyncMock, patch

import pytest

from app.routers import predict as predict_router
from app.exceptions import WrongItemIdError
from app.services.moderation import (
    ModelPredictionError,
    ModelUnavailableError,
)


@pytest.mark.parametrize(
    "probability,payload_overrides,expected",
    [
        (0.8, {"is_verified_seller": False, "images_qty": 0}, {'is_violation': True, 'probability': 0.8}),
        (0.2, {"is_verified_seller": True, "images_qty": 2}, {'is_violation': False, 'probability': 0.2}),
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
    assert response.json() == expected


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


def test_simple_predict_positive(client):
    with patch(
        "app.repositories.items.ItemRepository.get_item_with_user",
        new=AsyncMock(
            return_value={
                "seller_id": 11,
                "is_verified_seller": False,
                "item_id": 101,
                "name": "Item",
                "description": "Description",
                "category": 2,
                "images_qty": 1,
            }
        ),
    ), patch.object(
        predict_router.model_provider, "predict_proba", return_value=0.8
    ):
        response = client.post("/simple_predict", json={"item_id": 101})
    assert response.status_code == 200
    assert response.json()["is_violation"] is True


def test_simple_predict_negative(client):
    with patch(
        "app.repositories.items.ItemRepository.get_item_with_user",
        new=AsyncMock(
            return_value={
                "seller_id": 12,
                "is_verified_seller": True,
                "item_id": 202,
                "name": "Item",
                "description": "Description",
                "category": 2,
                "images_qty": 2,
            }
        ),
    ), patch.object(
        predict_router.model_provider, "predict_proba", return_value=0.2
    ):
        response = client.post("/simple_predict", json={"item_id": 202})
    assert response.status_code == 200
    assert response.json()["is_violation"] is False


def test_async_predict_success(client_with_kafka_mock):
    client, producer = client_with_kafka_mock
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.create_pending",
        new=AsyncMock(return_value=77),
    ):
        response = client.post("/async_predict", json={"item_id": 100})
    assert response.status_code == 200
    assert response.json()["task_id"] == 77
    assert response.json()["status"] == "pending"
    producer.send_moderation_request.assert_awaited_once_with(
        predict_router.MODERATION_TOPIC, 77, 100
    )


def test_async_predict_wrong_item_id(client):
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.create_pending",
        new=AsyncMock(side_effect=WrongItemIdError()),
    ):
        response = client.post("/async_predict", json={"item_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "wrong_item_id"


def test_close_item_deletes_item_and_cache(client):
    redis_mock = AsyncMock()
    redis_mock.aclose = AsyncMock(return_value=None)
    with patch(
        "app.repositories.items.ItemRepository.close_item",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.routers.predict.Redis.from_url", return_value=redis_mock
    ):
        response = client.post("/close", json={"item_id": 50})
    assert response.status_code == 200
    assert response.json() == {"status": "closed"}
    redis_mock.delete.assert_awaited_once_with("item_prediction:item_id:50")


def test_close_item_not_found(client):
    with patch(
        "app.repositories.items.ItemRepository.close_item",
        new=AsyncMock(return_value=False),
    ):
        response = client.post("/close", json={"item_id": 55})
    assert response.status_code == 404