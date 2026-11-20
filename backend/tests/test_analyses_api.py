import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app as fastapi_app


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


def test_analysis_run_returns_404_for_unknown_dataset() -> None:
    client = TestClient(fastapi_app)
    response = client.post(
        "/api/v1/analyses/run",
        json={"dataset_id": "non-existent-id", "question": "What is the total revenue?"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_get_analysis_returns_404_for_unknown_analysis() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/analyses/non-existent-id")
    assert response.status_code == 404


def test_list_analyses_returns_200() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/analyses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
