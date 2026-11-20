from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import HTTPException, status

from app.core.config import get_settings


def _as_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _infer_type(series: pd.Series) -> tuple[str, pd.Series | None]:
    non_empty = series.dropna().astype(str).str.strip()
    if non_empty.empty:
        return "unknown", None
    normalized = non_empty.str.lower()
    if normalized.isin({"true", "false", "yes", "no", "0", "1"}).mean() > 0.98:
        return "boolean", None
    numeric = pd.to_numeric(non_empty, errors="coerce")
    if numeric.notna().mean() > 0.98:
        return "integer" if (numeric.dropna() % 1 == 0).all() else "number", numeric
    dates = pd.to_datetime(non_empty, errors="coerce", format="mixed")
    if dates.notna().mean() > 0.9:
        return "date", dates
    return "string", None


def profile_csv(path: Path) -> tuple[dict, pd.DataFrame]:
    settings = get_settings()
    try:
        dataframe = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=True, nrows=settings.max_dataset_rows + 1)
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The file is not a valid CSV.") from error

    if dataframe.empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV must include at least one data row.")
    if len(dataframe) > settings.max_dataset_rows:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV files are limited to {settings.max_dataset_rows} rows.",
        )
    if not len(dataframe.columns) or any(not str(column).strip() for column in dataframe.columns):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV columns require non-empty names.")
    if dataframe.columns.duplicated().any():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV column names must be unique.")

    columns: list[dict] = []
    warnings: list[dict] = []
    for column in dataframe.columns:
        series = dataframe[column]
        inferred_type, converted = _infer_type(series)
        missing_count = int(series.isna().sum())
        profile: dict = {
            "name": str(column),
            "inferred_type": inferred_type,
            "missing_count": missing_count,
            "missing_percentage": round(missing_count / len(dataframe) * 100, 2),
            "distinct_count": int(series.nunique(dropna=True)),
            "sample_values": [str(value) for value in series.dropna().astype(str).head(5).tolist()],
        }
        if inferred_type in {"integer", "number"} and converted is not None:
            profile["numeric_statistics"] = {
                "minimum": _as_float(converted.min()),
                "maximum": _as_float(converted.max()),
                "mean": _as_float(converted.mean()),
                "median": _as_float(converted.median()),
            }
        if inferred_type == "date" and converted is not None:
            profile["date_coverage"] = {
                "minimum": converted.min().date().isoformat(),
                "maximum": converted.max().date().isoformat(),
            }
        if missing_count:
            warnings.append({"code": "missing_values", "message": f"{column} has {missing_count} missing values.", "column": str(column), "severity": "warning"})
        if inferred_type == "unknown":
            warnings.append({"code": "empty_column", "message": f"{column} contains no usable values.", "column": str(column), "severity": "warning"})
        columns.append(profile)

    duplicate_count = int(dataframe.duplicated().sum())
    if duplicate_count:
        warnings.append({"code": "duplicate_rows", "message": f"{duplicate_count} duplicate rows detected.", "column": None, "severity": "warning"})
    return {
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "duplicate_row_count": duplicate_count,
        "columns": columns,
        "warnings": warnings,
    }, dataframe


def preview_csv(path: Path, limit: int) -> tuple[list[str], list[dict]]:
    dataframe = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=True, nrows=limit)
    safe = dataframe.where(pd.notna(dataframe), None)
    return [str(column) for column in safe.columns], safe.to_dict(orient="records")

