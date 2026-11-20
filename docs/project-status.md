# Project status

## Goal

InsightPilot AI is an evidence-backed business analytics application that
profiles CSV data, plans analysis with an LLM, executes constrained tools, and
records transparent analysis history.

## Current status

Phases 1 through 6 are fully implemented and verified.

## Completed and Verified Features

- **FastAPI Backend**: Complete REST API with CORS, liveness check, and lifespan schema management.
- **React Frontend**: Full 3-tab UI (Dataset Workspace, Autonomous Analysis Workspace, Execution History) built with React 19, TypeScript, Vite, and Tailwind CSS.
- **Deterministic Retail Dataset**: Generates 20,000 clean and 20,150 messy retail records with JSON ground truth.
- **CSV Validation & Profiler**: Pandas quality profiling (schema, nulls, duplicates, value ranges, and defects).
- **DuckDB Analytical Engine**: Read-only query execution with memory limits and zero duplicate data storage.
- **SQL Security Validator**: SQLGlot AST validation enforcing single SELECT queries, allowlisted functions, and mandatory row limits.
- **Gemini Structured Planning**: Validated JSON schema generation for analysis plans and SQL proposals.
- **AI Error Recovery**: Automatic correction of SQL execution errors with retry attempts.
- **AI Business Reports**: Automatic synthesis of executive summaries, key findings, and recommendations based on verified execution data.
- **Analysis History**: Transparent tracking of execution attempts, run durations, generated SQL, and results.
- **Interactive Visualizations**: Dynamic SVG bar charts for numerical vs categorical results.

## Environment & Dependency Notes

- **Python Virtual Environment**: Project root `.venv` (Python 3.14.5) is fully installed and verified.
- **Database Support**: Zero-config SQLite default (`sqlite:///./insightpilot.db`) with full PostgreSQL compatibility via `DATABASE_URL`.
- **Pytest Configuration**: Configured with `addopts = --basetemp=../.pytest-tmp` in `backend/pytest.ini`.
- **Docker Python Sandbox**: Docker CLI installed; execution isolated in container. Host execution is prohibited. Marked blocked when Docker Desktop engine is not running.

- **Unified Single-Screen Workflow**: Combined dataset upload, automatic dashboard, and conversational analysis into a unified workspace journey.
- **Automatic Deterministic Dashboard**: `/api/v1/datasets/{id}/dashboard` calculates KPIs, monthly trends, category breakdowns, and dynamic suggested questions instantly in DuckDB without LLM hallucinations.
- **Context-Aware Follow-Up Conversations**: Supports multi-turn questions where Gemini resolves pronouns and relative references using previous verified analyses.
- **Collapsible Data Quality Drawer**: Technical schema, null distributions, duplicate warnings, and 20-row preview stay accessible without cluttering the business overview.

## Test Results

- Backend tests: 15 passed (`pytest backend/tests`).
- Frontend build: Passed (`npm run build` with Recharts & Lucide icons).
- End-to-end integration: Verified via live TestClient and browser-ready endpoints on NVIDIA NIM & Gemini.

## Recent Major Milestones (Complete UI/UX & Analytical Redesign)

- **SaaS Application Shell**: Redesigned shell with responsive top navigation (Workspace, Datasets, History), clean warm-slate typography, and subtle shadows.
- **Upload-First Landing Experience**: Drag-and-drop CSV onboarding zone with format and size badges, plus quick-resume pills for recent datasets.
- **Corrected Business Analytics**: Replaced invalid "Sum of unit_price" calculations with true additive revenue measures (`net_revenue`, derived sales volume, AOV per unique order, and units sold).
- **Interactive Recharts Visuals**: Replaced generic progress bars with dynamic Recharts Line and Bar charts for time-series trends and category rankings.
- **Adaptive AI Answers**: Streamlined responses so simple count questions receive direct answers with single-metric callouts, while comparison/causal questions receive rich evidence and charts.
- **Methodology & Clean Presentation**: Moved technical SQL statements into an optional "How this was calculated" plain-English accordion with developer audit toggles.
- **NVIDIA NIM Integration**: Added full support for NVIDIA NIM API (`nvidia/nemotron-3.5-bolt-e4b`) alongside Gemini with multi-model fallback.
