import csv
import tempfile
from pathlib import Path
import pytest

from app.rag.indexer import DatasetRagIndexer, get_token_count, deterministic_embedding
from app.rag.retriever import DatasetRagRetriever
from app.rag.router import classify_query
from app.rag.hybrid_executor import execute_semantic_rag, build_hybrid_filter
from app.schemas.analysis import RagEvidenceItem


def test_token_counting():
    text = "InsightPilot AI is a hybrid RAG-powered data analyst."
    count = get_token_count(text)
    assert count > 0


def test_deterministic_embedding():
    vec1 = deterministic_embedding("broken packaging and damaged item")
    vec2 = deterministic_embedding("broken packaging and damaged item")
    vec3 = deterministic_embedding("high annual gross revenue")
    
    assert len(vec1) == 384
    # Identical texts yield identical vectors
    assert abs(float((vec1 * vec2).sum()) - 1.0) < 1e-4
    # Different semantic texts have lower cosine similarity
    assert (vec1 * vec3).sum() < 0.9


def test_rag_indexer_and_retriever():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csv_file = tmp_path / "test.csv"
        
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["order_id", "product", "notes", "revenue"])
            writer.writerow(["ORD-1", "Laptop", "Customer complained about cracked screen", "1200"])
            writer.writerow(["ORD-2", "Phone", "Fast shipping and perfect condition", "800"])
            writer.writerow(["ORD-3", "Monitor", "Late delivery and damaged box", "300"])

        profile = {
            "row_count": 3,
            "column_count": 4,
            "columns": [
                {"name": "order_id", "inferred_type": "string"},
                {"name": "product", "inferred_type": "string"},
                {"name": "notes", "inferred_type": "string"},
                {"name": "revenue", "inferred_type": "integer"},
            ]
        }

        indexer = DatasetRagIndexer(dataset_id="test_ds", csv_path=csv_file, index_dir=tmp_path)
        meta = indexer.build_index(profile=profile, content_sha256="hash123")
        assert meta["chunk_count"] > 0
        assert indexer.is_indexed("hash123") is True

        retriever = DatasetRagRetriever(index_file=indexer.index_file, chunks_file=indexer.chunks_file)
        results = retriever.search("cracked screen", top_k=2)
        assert len(results) > 0
        assert any("cracked" in r.text.lower() or "screen" in r.text.lower() for r in results)


def test_query_router():
    assert classify_query("What is the total net revenue for each month?") == "structured_sql"
    assert classify_query("Show the average unit price across regions") == "structured_sql"
    assert classify_query("What complaints mention delayed delivery?") == "semantic_rag"
    assert classify_query("Find comments describing broken products") == "semantic_rag"
    assert classify_query("How many orders mention defective items?") == "hybrid"
    assert classify_query("What is the total revenue for orders with damaged packaging?") == "hybrid"


def test_hybrid_filter_builder():
    evidence = [
        RagEvidenceItem(chunk_id="c1", chunk_type="record_text", score=0.88, text="Damaged box", row_id=5),
        RagEvidenceItem(chunk_id="c2", chunk_type="record_text", score=0.82, text="Broken screen", row_id=12),
    ]
    filter_sql, matched_ids = build_hybrid_filter(evidence)
    assert matched_ids == [5, 12]
    assert filter_sql == "__row_id__ IN (5, 12)"


def test_semantic_rag_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csv_file = tmp_path / "test.csv"
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "feedback"])
            writer.writerow(["1", "Delivery was delayed by two weeks"])
            writer.writerow(["2", "Excellent service"])

        profile = {"row_count": 2, "column_count": 2, "columns": [{"name": "feedback", "inferred_type": "string"}]}
        indexer = DatasetRagIndexer("test_semantic", csv_file, index_dir=tmp_path)
        indexer.build_index(profile)
        retriever = DatasetRagRetriever(indexer.index_file, indexer.chunks_file)

        plan, sql, columns, rows, report, evidence = execute_semantic_rag(
            "What complaints mention delayed delivery?", retriever, "orders.csv"
        )
        assert len(plan.steps) == 1
        assert "FAISS" in sql
        assert report.executive_summary is not None
        assert len(report.key_findings) > 0
