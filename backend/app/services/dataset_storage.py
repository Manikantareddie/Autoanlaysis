from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

CHUNK_SIZE = 1024 * 1024
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def clean_filename(filename: str) -> str:
    candidate = Path(filename).name
    cleaned = SAFE_FILENAME.sub("_", candidate).strip("._")
    return cleaned or "dataset.csv"


async def persist_csv(upload: UploadFile) -> tuple[str, Path, int, str]:
    settings = get_settings()
    if not upload.filename or Path(upload.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only .csv files are supported.")

    dataset_id = str(uuid.uuid4())
    destination_dir = settings.storage_dir / dataset_id
    destination_dir.mkdir(parents=True, exist_ok=False)
    destination = destination_dir / "source.csv"
    maximum_bytes = settings.max_upload_size_mb * 1024 * 1024
    digest = hashlib.sha256()
    written = 0

    try:
        with destination.open("wb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                written += len(chunk)
                if written > maximum_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"CSV files are limited to {settings.max_upload_size_mb} MB.",
                    )
                digest.update(chunk)
                target.write(chunk)
        validate_csv_encoding(destination)
        return dataset_id, destination, written, digest.hexdigest()
    except Exception:
        shutil.rmtree(destination_dir, ignore_errors=True)
        raise
    finally:
        await upload.close()


def validate_csv_encoding(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            sample = source.read(4096)
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV must be UTF-8 encoded.") from error
    if not sample.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV file is empty.")

