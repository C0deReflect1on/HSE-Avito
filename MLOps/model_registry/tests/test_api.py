import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_get_model():
    """Тест 1: регистрация модели и получение её метадаты."""
    response = client.post(
        "/models",
        data={
            "name": "test-model",
            "version": "v1",
            "model_type": "catboost",
            "dataset": "hdfs://data/train.csv",
            "owner": "mlds_1",
        },
        files={"file": ("model.bin", io.BytesIO(b"fake model binary"), "application/octet-stream")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-model"
    assert data["stage"] == "experimental"
    model_id = data["id"]

    # Получить по id
    response = client.get(f"/models/{model_id}")
    assert response.status_code == 200
    assert response.json()["version"] == "v1"


def test_search_models():
    """Тест 2: поиск по параметрам."""
    # Зарегистрируем вторую модель
    client.post(
        "/models",
        data={
            "name": "search-model",
            "version": "v1",
            "model_type": "logreg",
            "dataset": "hdfs://data/search.csv",
            "owner": "mlds_3",
        },
        files={"file": ("model.bin", io.BytesIO(b"data"), "application/octet-stream")},
    )

    # Ищем по model_type
    response = client.get("/models", params={"model_type": "logreg"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert all(r["model_type"] == "logreg" for r in results)