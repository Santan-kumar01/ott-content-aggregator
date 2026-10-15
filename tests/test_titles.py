from fastapi.testclient import TestClient

from src.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


def test_create_title_invalid_year():
    payload = {
        "name": "Test Movie",
        "description": "Testing invalid year",
        "content_type": "movie",
        "release_year": 1700,
        "genre": "Drama",
        "platform": "Netflix",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/titles/", json=payload)

    assert response.status_code == 422


def test_create_title_invalid_content_type():
    payload = {
        "name": "Test Documentary",
        "description": "Testing invalid content type",
        "content_type": "documentary",
        "release_year": 2020,
        "genre": "Documentary",
        "platform": "Netflix",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/titles/", json=payload)

    assert response.status_code == 422


def test_unknown_title_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/v1/titles/999999")

    assert response.status_code == 404
