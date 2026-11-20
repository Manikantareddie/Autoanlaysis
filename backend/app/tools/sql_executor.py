from pathlib import Path
import duckdb
from fastapi import HTTPException, status
from app.validators.sql import validate_sql

def execute_read_only(dataset_db: Path, sql: str, max_rows: int = 1000) -> tuple[str, list[str], list[list[object]]]:
    safe_sql = validate_sql(sql, max_rows)
    try:
        connection = duckdb.connect(str(dataset_db), read_only=True, config={"threads": "1", "memory_limit": "256MB"})
        try:
            result = connection.execute(safe_sql)
            columns = [item[0] for item in result.description]
            rows = result.fetchmany(max_rows)
            return safe_sql, columns, [list(row) for row in rows]
        finally:
            connection.close()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Database execution error: {error}") from error

