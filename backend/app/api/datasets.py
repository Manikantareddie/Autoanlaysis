from __future__ import annotations

import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, get_session
from app.models.dataset import Dataset
from app.schemas.datasets import (
    DatasetDashboard,
    DatasetDetail,
    DatasetPreview,
    DatasetProfile,
    DatasetSummary,
)
from app.services.dashboard import compute_dataset_dashboard
from app.services.dataset_storage import clean_filename, persist_csv
from app.services.duckdb_store import create_dataset_database
from app.services.profiler import preview_csv, profile_csv
from app.rag.indexer import DatasetRagIndexer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def _summary(dataset: Dataset) -> DatasetSummary:
    return DatasetSummary(
        id=dataset.id,
        original_filename=dataset.original_filename,
        file_size_bytes=dataset.file_size_bytes,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        status=dataset.status,
        created_at=dataset.created_at,
    )


def _get_dataset(dataset_id: str, session: Session) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return dataset


def _build_rag_index_async(dataset_id: str, csv_path: Path, profile: dict, digest: str, req_id: str) -> None:
    t0 = time.perf_counter()
    try:
        indexer = DatasetRagIndexer(dataset_id=dataset_id, csv_path=csv_path)
        indexer.build_index(profile=profile, content_sha256=digest)
        dur = (time.perf_counter() - t0) * 1000
        logger.info("[%s] Async RAG indexing completed for dataset %s in %.1f ms", req_id, dataset_id, dur)
    except Exception as exc:
        logger.warning("[%s] Async RAG indexing skipped/failed for dataset %s: %s", req_id, dataset_id, exc)


@router.post("", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session),
) -> DatasetDetail:
    """Persist, validate, profile, and register a CSV under application control."""
    req_id = uuid.uuid4().hex[:8]
    t_start = time.perf_counter()
    ts_iso = datetime.now(timezone.utc).isoformat()
    raw_name = file.filename or "dataset.csv"
    logger.info("[%s] [%s] Dataset upload initiated: filename='%s'", req_id, ts_iso, raw_name)

    dataset_id, csv_path, file_size, digest = await persist_csv(file)
    dataset_dir = csv_path.parent
    t_persist = (time.perf_counter() - t_start) * 1000
    logger.info("[%s] CSV persisted (%d bytes) in %.1f ms", req_id, file_size, t_persist)

    try:
        t_prof_start = time.perf_counter()
        profile, _ = profile_csv(csv_path)
        t_prof = (time.perf_counter() - t_prof_start) * 1000
        logger.info(
            "[%s] Profiling completed in %.1f ms: %d rows, %d cols",
            req_id,
            t_prof,
            profile["row_count"],
            profile["column_count"],
        )

        t_db_start = time.perf_counter()
        duckdb_path = dataset_dir / "analysis.duckdb"
        create_dataset_database(csv_path, duckdb_path)
        t_db = (time.perf_counter() - t_db_start) * 1000
        logger.info("[%s] DuckDB store created in %.1f ms", req_id, t_db)

        Base.metadata.create_all(bind=engine)
        dataset = Dataset(
            id=dataset_id,
            original_filename=clean_filename(raw_name),
            storage_path=str(csv_path.resolve()),
            duckdb_path=str(duckdb_path.resolve()),
            content_sha256=digest,
            file_size_bytes=file_size,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            schema_json=profile["columns"],
            profile_json=profile,
            status="ready",
        )
        session.add(dataset)
        session.commit()
        session.refresh(dataset)

        # Offload RAG indexing to background task so the HTTP response returns immediately
        background_tasks.add_task(_build_rag_index_async, dataset_id, csv_path, profile, digest, req_id)

        total_elapsed = (time.perf_counter() - t_start) * 1000
        logger.info("[%s] Dataset %s registered and ready in %.1f ms", req_id, dataset_id, total_elapsed)
        return DatasetDetail(**_summary(dataset).model_dump(), profile=DatasetProfile.model_validate(dataset.profile_json))
    except HTTPException:
        shutil.rmtree(dataset_dir, ignore_errors=True)
        raise
    except Exception as error:
        session.rollback()
        shutil.rmtree(dataset_dir, ignore_errors=True)
        logger.error("[%s] Dataset processing failed: %s", req_id, error, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset processing error: {error}",
        ) from error


@router.get("", response_model=list[DatasetSummary])
def list_datasets(session: Session = Depends(get_session)) -> list[DatasetSummary]:
    datasets = session.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    return [_summary(dataset) for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: str, session: Session = Depends(get_session)) -> DatasetDetail:
    dataset = _get_dataset(dataset_id, session)
    return DatasetDetail(**_summary(dataset).model_dump(), profile=DatasetProfile.model_validate(dataset.profile_json))


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def get_dataset_profile(dataset_id: str, session: Session = Depends(get_session)) -> DatasetProfile:
    return DatasetProfile.model_validate(_get_dataset(dataset_id, session).profile_json)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> DatasetPreview:
    dataset = _get_dataset(dataset_id, session)
    csv_path = Path(dataset.storage_path)
    if not csv_path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Dataset source file is unavailable.")
    columns, rows = preview_csv(csv_path, limit)
    return DatasetPreview(dataset_id=dataset.id, columns=columns, rows=rows, limit=limit)


@router.get("/{dataset_id}/dashboard", response_model=DatasetDashboard)
def get_dataset_dashboard(dataset_id: str, session: Session = Depends(get_session)) -> DatasetDashboard:
    dataset = _get_dataset(dataset_id, session)
    duckdb_path = Path(dataset.duckdb_path)
    if not duckdb_path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Dataset DuckDB store is unavailable.")
    dashboard_data = compute_dataset_dashboard(duckdb_path)
    return DatasetDashboard(dataset_id=dataset.id, **dashboard_data)
