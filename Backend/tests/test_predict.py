from unittest.mock import Mock

from app.routers import predict as predict_router
from app.services.moderation import ModerationError, ModerationService


def test_predict_positive_for_verified_seller(client, payload_factory):
    payload = payload_factory(is_verified_seller=True, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True


def test_predict_negative_for_unverified_without_images(client, payload_factory):
    payload = payload_factory(is_verified_seller=False, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is False


def test_predict_positive_for_unverified_with_images(client, payload_factory):
    payload = payload_factory(is_verified_seller=False, images_qty=1)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True


def test_predict_validation_error(client, payload_factory):
    payload = payload_factory(images_qty=-1)
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_business_error(client, payload_factory, monkeypatch):
    availability_checker = Mock()
    availability_checker.ensure_available.side_effect = ModerationError(
        "service temporarily unavailable"
    )
    moderation_service = ModerationService(
        predict_router.repository,
        availability_checker,
    )
    monkeypatch.setattr(predict_router, "moderation_service", moderation_service)
    response = client.post("/predict", json=payload_factory())
    assert response.status_code == 500
    assert response.json() == {"detail": "service temporarily unavailable"}
