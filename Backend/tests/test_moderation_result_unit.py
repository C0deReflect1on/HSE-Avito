from unittest.mock import AsyncMock, patch


def test_moderation_result_pending(client):
    row = {"id": 10, "status": "pending"}
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.get_by_id",
        new=AsyncMock(return_value=row),
    ):
        response = client.get("/moderation_result/10")

    assert response.status_code == 200
    assert response.json() == {"task_id": 10, "status": "pending"}


def test_moderation_result_completed(client):
    row = {"id": 11, "status": "completed", "is_violation": True, "probability": 0.81}
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.get_by_id",
        new=AsyncMock(return_value=row),
    ):
        response = client.get("/moderation_result/11")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": 11,
        "status": "completed",
        "result": {"is_violation": True, "probability": 0.81},
    }


def test_moderation_result_failed(client):
    row = {"id": 12, "status": "failed", "error_message": "broken"}
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.get_by_id",
        new=AsyncMock(return_value=row),
    ):
        response = client.get("/moderation_result/12")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": 12,
        "status": "failed",
        "error_message": "broken",
    }


def test_moderation_result_not_found(client):
    with patch(
        "app.repositories.moderation_repository.ModerationRepository.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        response = client.get("/moderation_result/404")

    assert response.status_code == 404
