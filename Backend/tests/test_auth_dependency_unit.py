import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies import get_current_account
from app.exceptions import InvalidTokenError
from app.main import app
from app.schemas import Account

pytestmark = pytest.mark.unit


def _make_mock_kafka_producer():
    mock = MagicMock()
    mock.start = AsyncMock(return_value=None)
    mock.stop = AsyncMock(return_value=None)
    mock.send_moderation_request = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def client_without_auth_override():
    mock_producer = _make_mock_kafka_producer()
    with patch("app.main.KafkaProducer", return_value=mock_producer), patch(
        "app.main.db.connect", new=AsyncMock(return_value=None)
    ), patch("app.main.db.disconnect", new=AsyncMock(return_value=None)), patch(
        "app.main.predict_router_module.model_provider.load", return_value=None
    ):
        with TestClient(app) as client:
            yield client


def test_valid_token_returns_account():
    request = SimpleNamespace(cookies={"access_token": "token"})
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        return_value={"user_id": 1, "login": "alice"},
    ), patch(
        "app.repositories.account_repository.AccountRepository.get_by_id",
        new=AsyncMock(return_value=Account(id=1, login="alice", is_blocked=False)),
    ):
        account = asyncio.run(get_current_account(request))
    assert account.id == 1


def test_missing_cookie():
    request = SimpleNamespace(cookies={})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_account(request))
    assert exc.value.status_code == 401


def test_invalid_token():
    request = SimpleNamespace(cookies={"access_token": "bad-token"})
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        side_effect=InvalidTokenError("bad token"),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_account(request))
    assert exc.value.status_code == 401


def test_expired_token():
    request = SimpleNamespace(cookies={"access_token": "expired-token"})
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        side_effect=InvalidTokenError("expired"),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_account(request))
    assert exc.value.status_code == 401


def test_blocked_account():
    request = SimpleNamespace(cookies={"access_token": "token"})
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        return_value={"user_id": 10, "login": "blocked"},
    ), patch(
        "app.repositories.account_repository.AccountRepository.get_by_id",
        new=AsyncMock(return_value=Account(id=10, login="blocked", is_blocked=True)),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_account(request))
    assert exc.value.status_code == 401


def test_account_not_found():
    request = SimpleNamespace(cookies={"access_token": "token"})
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        return_value={"user_id": 77, "login": "nobody"},
    ), patch(
        "app.repositories.account_repository.AccountRepository.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_account(request))
    assert exc.value.status_code == 401


def test_predict_without_auth(client_without_auth_override):
    response = client_without_auth_override.post(
        "/predict",
        json={
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 10,
            "name": "Item",
            "description": "Description",
            "category": 2,
            "images_qty": 1,
        },
    )
    assert response.status_code == 401


def test_predict_with_auth(client_without_auth_override):
    with patch(
        "app.services.auth_service.AuthService.verify_token",
        return_value={"user_id": 1, "login": "alice"},
    ), patch(
        "app.repositories.account_repository.AccountRepository.get_by_id",
        new=AsyncMock(return_value=Account(id=1, login="alice", is_blocked=False)),
    ), patch(
        "app.routers.predict.model_provider.predict_proba",
        return_value=0.8,
    ):
        response = client_without_auth_override.post(
            "/predict",
            cookies={"access_token": "valid-token"},
            json={
                "seller_id": 1,
                "is_verified_seller": False,
                "item_id": 10,
                "name": "Item",
                "description": "Description",
                "category": 2,
                "images_qty": 1,
            },
        )
    assert response.status_code == 200
