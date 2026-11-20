# Architecture decisions

## 2026-11-20 — Start with a real data foundation

Phase 1 uses a deterministic stdlib generator instead of committed CSV
artifacts. This keeps the repository small, makes the demo reproducible, and
gives later tests known aggregate values.

## 2026-11-20 — Separate metadata from analytical data

PostgreSQL will store metadata and execution history; source datasets and
generated files will remain controlled filesystem/object-storage artifacts.
DuckDB will be a constrained analytical executor rather than the system of
record.

## 2026-11-20 — No generated-code execution in the API process

Python execution will be introduced only with the Docker sandbox in Phase 5.
There is no host-process fallback.

## 2026-11-20 — Persist source CSV once, register it in DuckDB

Uploads live in a UUID-owned storage directory. A per-dataset DuckDB file
contains only a view registered over that controlled source file. This avoids
duplicating large datasets while reserving DuckDB for the later restricted
analytical-query boundary.

## 2026-11-20 — Profile deterministically before AI sees data

Pandas calculates schema, missingness, duplicates, basic numeric values, and
date coverage. The LLM will later receive this bounded profile instead of the
full upload.

## 2026-11-20 — Zero-config database portability

To prevent port collision with native host database services and eliminate
friction during local development, SQLAlchemy engine initialization supports
both SQLite (`sqlite:///./insightpilot.db`) and PostgreSQL (`postgresql+psycopg://...`).
Tables and relations use standard SQL-compliant types compatible with both engines.

## 2026-11-20 — GenAI client reuse via LRU cache

Instantiating transient `genai.Client` instances inside endpoint handlers risks
premature closure of the underlying HTTPX connection pool during retry or async
event loops. `_client()` is memoized with `@lru_cache` to preserve healthy HTTP
connections.

## 2026-11-20 — Preserve Docker security boundary

If the Docker daemon is unreachable or WSL2 is not installed, Python sandbox
execution remains strictly blocked. Code is never evaluated in the host or API
process as a fallback, preserving sandbox integrity. SQL execution on DuckDB
serves as the primary verified analytical tool.

## 2026-11-20 — Expanded SQLGlot AST validation for temporal & string analytics

The SQL validator allowlist was expanded to support DuckDB time-series and
string transformations (such as `STRFTIME`, `TIME_TO_STR`, `EXTRACT`, `ABS`,
`CONCAT`) while strictly enforcing read-only single-statement execution against
the isolated `dataset` table. Disallowed AST violations are fed back into the
LLM error recovery loop for automated dialect correction.

## 2026-11-20 — Minimalist human-centric design & currency neutrality

The frontend was completely refactored to eliminate AI-cliché purple/neon gradients
in favor of a calm, warm-neutral slate/zinc palette (`#f8fafc`, `#ffffff`, `#e2e8f0`, `#0f172a`).
Currency symbols (`$`) were removed across all metric calculations to support universal
domain datasets (healthcare, telemetry, education, logistics) with clean locale-formatted numbers.
The initial view is kept strictly clean, prompting the user for dataset upload rather
than auto-selecting synthetic test records.


