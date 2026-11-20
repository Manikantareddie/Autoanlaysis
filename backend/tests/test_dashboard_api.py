import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app as fastapi_app

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data" / "scripts" / "generate_retail_data.py"
SPEC = importlib.util.spec_from_file_location("retail_generator", SCRIPT)
assert SPEC and SPEC.loader
retail_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retail_generator)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


def test_dashboard_endpoint_returns_404_for_unknown_dataset() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/datasets/non-existent-id/dashboard")
    assert response.status_code == 404


def test_dashboard_endpoint_computes_kpis_and_charts(tmp_path: Path) -> None:
    retail_generator.generate(tmp_path)
    clean_csv = tmp_path / "retail_sales_clean.csv"

    client = TestClient(fastapi_app)
    with clean_csv.open("rb") as f:
        upload_resp = client.post(
            "/api/v1/datasets",
            files={"file": ("retail_sales_clean.csv", f, "text/csv")},
        )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    dash_resp = client.get(f"/api/v1/datasets/{dataset_id}/dashboard")
    assert dash_resp.status_code == 200
    data = dash_resp.json()

    assert data["dataset_id"] == dataset_id
    assert len(data["kpis"]) >= 3
    assert any("Total" in k["label"] for k in data["kpis"])
    assert len(data["charts"]) >= 1
    assert len(data["suggested_questions"]) >= 1
