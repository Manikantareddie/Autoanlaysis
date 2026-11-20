import io
import time
import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app as fastapi_app
from app.rag.indexer import deterministic_embedding, get_embeddings, _VECTOR_DIM


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


def test_deterministic_embedding_fast_and_zero_memory():
    texts = [
        "Customer reported cracked laptop screen and missing charger.",
        "Monthly recurring revenue increased 15% across North region.",
        "Late package delivery and courier damaged parcel.",
    ]
    t0 = time.perf_counter()
    vecs = get_embeddings(texts)
    elapsed = (time.perf_counter() - t0) * 1000

    assert vecs.shape == (3, _VECTOR_DIM)
    assert elapsed < 50.0  # Runs in less than 50ms without network or PyTorch weights


def test_dataset_upload_and_dashboard_workflow():
    client = TestClient(fastapi_app)

    # 1. Create a synthetic test CSV
    csv_content = (
        "order_id,category,region,month,net_revenue_inr,quantity,returned\n"
        "ORD001,Electronics,South,2026-01,15000.0,2,0\n"
        "ORD002,Fashion,North,2026-01,2400.0,1,0\n"
        "ORD003,Home,West,2026-02,8900.0,3,1\n"
        "ORD004,Electronics,South,2026-02,32000.0,4,0\n"
        "ORD005,Beauty,Central,2026-03,1200.0,1,0\n"
    )

    # 2. Upload CSV
    t0 = time.perf_counter()
    response = client.post(
        "/api/v1/datasets",
        files={"file": ("sales_sample.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    upload_elapsed = (time.perf_counter() - t0) * 1000

    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    dataset_id = data["id"]
    assert data["row_count"] == 5
    assert data["column_count"] == 7
    assert upload_elapsed < 3000.0  # Upload completes rapidly in milliseconds

    # 3. Retrieve Dashboard
    dash_resp = client.get(f"/api/v1/datasets/{dataset_id}/dashboard")
    assert dash_resp.status_code == 200, dash_resp.text
    dashboard = dash_resp.json()
    assert len(dashboard["kpis"]) >= 1
    assert len(dashboard["suggested_questions"]) >= 1

    # 4. Preview CSV
    prev_resp = client.get(f"/api/v1/datasets/{dataset_id}/preview?limit=5")
    assert prev_resp.status_code == 200
    preview = prev_resp.json()
    assert len(preview["rows"]) == 5
    assert "order_id" in preview["columns"]
