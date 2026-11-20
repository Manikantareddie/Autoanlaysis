# InsightPilot AI — Master Specification

## 1. System Vision

InsightPilot AI is an autonomous, evidence-backed data analyst application designed to empower non-technical users to inspect complex datasets, ask business questions, and receive transparent analysis plans, safe query execution, interactive visualizations, and executive business reports.

## 2. Architecture Overview

```
Frontend (React 19 + TypeScript + Vite + Tailwind CSS)
    |
    | REST API (JSON)
    v
FastAPI Backend (app.main:app)
    ├── Metadata Store: SQLite (default zero-config) / PostgreSQL
    ├── File Storage: Controlled storage/datasets/<uuid>/source.csv
    ├── Profiler: Pandas dataset profiling (schema, nulls, duplicates, warnings)
    ├── Analytical Engine: DuckDB in-memory read-only views
    ├── Agent System: Google Gemini 2.5 Flash + LangGraph StateGraph
    ├── Security Validator: SQLGlot AST allowlist & row bounding (LIMIT 1000)
    └── Sandbox Boundary: Docker isolation (for Python execution when available)
```

## 3. Data & Execution Boundaries

1. **Storage Safety**:
   - Uploaded files are assigned UUID directories under `storage/datasets/<uuid>/`.
   - Never trust client-provided filenames for filesystem operations.
   - Enforce 25 MB max size and 100,000 row limits.
   - Verify UTF-8 encoding and valid delimited structure.
2. **Analytical Tool Execution**:
   - DuckDB operates with `read_only=True`, 256MB memory limit, and single thread.
   - SQL queries must pass `validate_sql` AST checks before execution.
   - Prohibited SQL operations: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `ATTACH`, `COPY`, `PRAGMA`.
   - Function allowlist: `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `COALESCE`, `ROUND`, `DATE_TRUNC`, `CAST`, `LOWER`, `UPPER`, `NULLIF`.
3. **Sandbox Python Isolation**:
   - Docker container `insightpilot-python-sandbox:local` configured with `--network none`, `--read-only`, dropped capabilities, memory & CPU limits, non-root `analyst` user.
   - Python execution blocked when Docker daemon is unavailable.

## 4. Endpoints Specification

- `GET /health`: Service liveness and environment.
- `POST /api/v1/datasets`: Upload, profile, and register CSV.
- `GET /api/v1/datasets`: List all uploaded datasets.
- `GET /api/v1/datasets/{id}`: Detailed dataset profile.
- `GET /api/v1/datasets/{id}/preview`: Bounded first N rows (1–100).
- `POST /api/v1/analyses/run`: Run AI analysis pipeline (plan, SQL, DuckDB execution, error correction, report).
- `GET /api/v1/analyses`: List analyses (optional `?dataset_id=...`).
- `GET /api/v1/analyses/{id}`: Full execution history and audit traces.
