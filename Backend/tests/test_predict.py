from unittest.mock import patch

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