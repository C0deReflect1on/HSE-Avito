from app.routers.predict import moderation_service


def make_payload(**overrides):
    payload = {
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 10,
        "name": "Item",
        "description": "Description",
        "category": 3,
        "images_qty": 1,
    }
    payload.update(overrides)
    return payload


def test_predict_positive_for_verified_seller(client):
    payload = make_payload(is_verified_seller=True, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True


def test_predict_negative_for_unverified_without_images(client):
    payload = make_payload(is_verified_seller=False, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is False


def test_predict_validation_error(client):
    payload = make_payload()
    payload.pop("seller_id")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_business_error(client):
    moderation_service.service_up = False
    try:
        response = client.post("/predict", json=make_payload())
        assert response.status_code == 500
        assert response.json() == {"detail": "service temporarily unavailable"}
    finally:
        moderation_service.service_up = True
