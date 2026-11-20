from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.rag.retriever import DatasetRagRetriever
from app.schemas.analysis import AnalysisPlan, BusinessReport, PlanStep, RagEvidenceItem

logger = logging.getLogger(__name__)


def execute_semantic_rag(
    question: str,
    retriever: DatasetRagRetriever,
    dataset_name: str = "dataset.csv",
) -> tuple[AnalysisPlan, str, list[str], list[list[Any]], BusinessReport, list[RagEvidenceItem]]:
    """Execute qualitative question using semantic vector retrieval and grounded synthesis."""
    evidence = retriever.search(question, top_k=6, min_score=0.10)
    
    plan = AnalysisPlan(
        objective=f"Semantic qualitative search for: '{question}'",
        required_columns=[],
        steps=[
            PlanStep(
                step_id=1,
                description="Retrieve semantically relevant records from FAISS vector index.",
                tool="python",
                expected_output="Top matched record snippets with similarity scores.",
            )
        ],
    )

    sql = "-- Qualitative semantic vector retrieval against FAISS index (IndexFlatIP)"
    columns = ["row_id", "similarity_score", "matched_evidence"]
    rows: list[list[Any]] = []
    findings: list[str] = []

    for ev in evidence:
        rows.append([ev.row_id if ev.row_id is not None else "-", ev.score, ev.text])
        ref = f"Record #{ev.row_id}" if ev.row_id else "Schema note"
        findings.append(f"{ref} (relevance: {ev.score:.2f}): {ev.text}")

    if not findings:
        findings.append("No strongly matching records found above semantic similarity threshold.")

    report = BusinessReport(
        executive_summary=(
            f"Semantic analysis of {dataset_name} for '{question}' identified "
            f"{len(evidence)} relevant observations from the dataset."
        ),
        key_findings=findings[:8],
        business_recommendations=[
            "Investigate recurring patterns identified in matched text records.",
            "Verify whether operational process adjustments are required based on customer or order feedback."
        ],
        data_caveats=[
            "Semantic search results reflect text similarity in recorded fields; unrecorded factors are not captured."
        ],
    )

    return plan, sql, columns, rows, report, evidence


def build_hybrid_filter(evidence: list[RagEvidenceItem]) -> tuple[str, list[int]]:
    """Extract matched row_ids to construct a deterministic DuckDB filter."""
    matched_row_ids = [ev.row_id for ev in evidence if ev.row_id is not None]
    if not matched_row_ids:
        return "", []
    ids_str = ", ".join(str(i) for i in matched_row_ids)
    filter_sql = f"__row_id__ IN ({ids_str})"
    return filter_sql, matched_row_ids
