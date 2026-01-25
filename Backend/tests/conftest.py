import pytest

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def payload_factory():
    def _factory(**overrides):
        payload = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 2,
            "images_qty": 2,
        }
        payload.update(overrides)
        return payload

    return _factory
