import pytest
from fastapi import HTTPException

from app.validators.sql import validate_sql


def test_validator_accepts_valid_select_query() -> None:
    sql = "SELECT product_id, SUM(gross_revenue) AS rev FROM dataset GROUP BY product_id"
    safe_sql = validate_sql(sql)

    assert "SELECT" in safe_sql
    assert "dataset" in safe_sql
    assert "LIMIT 1000" in safe_sql


def test_validator_respects_existing_limit() -> None:
    sql = "SELECT category, COUNT(*) as cnt FROM dataset GROUP BY category LIMIT 5"
    safe_sql = validate_sql(sql)

    assert "LIMIT 5" in safe_sql


def test_validator_rejects_ddl_and_dml() -> None:
    forbidden_queries = [
        "DROP TABLE dataset",
        "DELETE FROM dataset WHERE gross_revenue < 0",
        "UPDATE dataset SET discount = 0",
        "INSERT INTO dataset VALUES (1, 2)",
        "ALTER TABLE dataset ADD COLUMN hacked INT",
    ]
    for query in forbidden_queries:
        with pytest.raises(HTTPException) as exc_info:
            validate_sql(query)
        assert exc_info.value.status_code == 403


def test_validator_rejects_multiple_statements() -> None:
    sql = "SELECT * FROM dataset; DROP TABLE dataset;"
    with pytest.raises(HTTPException) as exc_info:
        validate_sql(sql)
    assert exc_info.value.status_code == 403


def test_validator_rejects_external_tables() -> None:
    sql = "SELECT * FROM information_schema.tables"
    with pytest.raises(HTTPException) as exc_info:
        validate_sql(sql)
    assert exc_info.value.status_code == 403


def test_validator_rejects_disallowed_functions() -> None:
    sql = "SELECT read_csv('secret.csv') FROM dataset"
    with pytest.raises(HTTPException) as exc_info:
        validate_sql(sql)
    assert exc_info.value.status_code == 403
