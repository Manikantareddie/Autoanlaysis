from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_service_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "insightpilot-api"


def test_cors_headers_allowed_for_vercel() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "https://autoanlaysis.vercel.app"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://autoanlaysis.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_options_preflight_for_datasets() -> None:
    client = TestClient(app)
    response = client.options(
        "/api/v1/datasets",
        headers={
            "Origin": "https://autoanlaysis.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://autoanlaysis.vercel.app"
    assert "POST" in response.headers.get("access-control-allow-methods", "")

