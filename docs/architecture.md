# Architecture

## Phase 1 boundary

Phase 2 adds CSV upload, controlled source storage, PostgreSQL dataset
metadata, Pandas profiling, a bounded preview endpoint, and a per-dataset
DuckDB database with a registered source view. It deliberately contains no LLM,
AI-generated SQL, or generated-code execution.

```text
React + TypeScript (localhost:5173)
        | dataset REST API
        v
FastAPI (localhost:8000)
        |-- application-controlled storage/source.csv
        |-- Pandas profiler
        |-- DuckDB analysis.duckdb (registered dataset view)
        v
PostgreSQL metadata

Synthetic data generator -> clean CSV + messy CSV + ground-truth JSON
```

## Intended production architecture

FastAPI will coordinate dataset storage/profiling, PostgreSQL metadata, isolated
DuckDB SQL execution, and a LangGraph workflow. Gemini is backend-only.
Generated Python will only run in a separately constrained Docker container.
Results and charts must be derived from executed tools, not model text.

## Data contract for fixtures

The clean data contains 20,000 records and 500 products across calendar year
2025. Discount is a decimal percentage. Gross revenue is the discounted line
value. Net revenue and gross profit are zero for returned/cancelled orders,
modelling refunds/cancellations. The messy fixture is a deliberate copy with
documented defects; it never replaces the clean truth.

## Security boundary roadmap

The upload endpoint writes only to UUID-owned application directories and does
not trust filenames as paths. It enforces configured byte/row limits, reads
UTF-8 CSV only, and rejects empty or malformed structures. Source files are
retained unchanged; profiling is read-only. Later phases will treat model
output, SQL, and Python as untrusted.

