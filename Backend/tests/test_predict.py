from unittest.mock import Mock

import pytest

from app.routers import predict as predict_router
from app.services.moderation import (
    ModerationError,
    ModerationService,
    ModelUnavailableError,
)


class StubModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, values):
        return [[1 - self.probability, self.probability]]


class FailingModel:
    def predict_proba(self, values):
        raise RuntimeError("boom")


def test_predict_positive(client, payload_factory):
    original_model = client.app.state.model
    client.app.state.model = StubModel(0.8)
    payload = payload_factory(is_verified_seller=False, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True
    client.app.state.model = original_model


def test_predict_negative(client, payload_factory):
    original_model = client.app.state.model
    client.app.state.model = StubModel(0.2)
    payload = payload_factory(is_verified_seller=True, images_qty=2)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is False
    client.app.state.model = original_model


def test_predict_validation_error(client, payload_factory):
    payload = payload_factory(images_qty="invalid")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_model_unavailable(client, payload_factory):
    client.app.state.model = None
    response = client.post("/predict", json=payload_factory())
    assert response.status_code == 503
    assert response.json()["detail"] == "moderation model is not loaded"


def test_predict_failure_returns_500(client, payload_factory):
    original_model = client.app.state.model
    client.app.state.model = FailingModel()
    response = client.post("/predict", json=payload_factory())
    assert response.status_code == 500
    assert response.json()["detail"] == "predictions are unavailable"
    client.app.state.model = original_model