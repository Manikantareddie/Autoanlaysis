# InsightPilot AI — Agent Architecture

InsightPilot AI employs constrained, structured agent workflows powered by Google Gemini and LangGraph.

## Core Design Principles

1. **Untrusted Data Boundary**: Dataset values and user inputs are strictly treated as data, never as prompt instructions.
2. **Deterministic Schemas**: All agent outputs are validated against Pydantic models via Gemini's structured output mechanism (`response_mime_type="application/json"` with `response_json_schema`).
3. **Execution Separation**: AI models only propose analytical plans, queries, or code; they never execute code directly. Execution is delegated to validated tools.

## Agent Workflows

### 1. Analysis Planner (`backend/app/agents/planner.py`)
- **Role**: Breaks down natural-language business questions into a structured multi-step analytical plan.
- **Input**: User question and bounded dataset profile (column names, inferred types, quality warnings).
- **Output Schema**: `AnalysisPlan` containing:
  - `objective`: High-level business goal
  - `required_columns`: List of dataset columns required
  - `steps`: 1 to 4 `PlanStep` items specifying step ID, description, tool type (`sql` or `python`), and expected output.

### 2. SQL Proposal Agent (`backend/app/agents/planner.py`)
- **Role**: Translates plan steps into a single read-only DuckDB SQL query.
- **Constraints**:
  - Target table must be `dataset`.
  - Prohibits CTEs, file operations, extension loading, or DDL/DML.
  - Restricted to allowlisted aggregate and scalar functions (`SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `ROUND`, `DATE_TRUNC`, `CAST`, `COALESCE`, `NULLIF`, `LOWER`, `UPPER`).
- **Output Schema**: `SqlProposal` with `sql` and `explanation`.

### 3. Error Recovery Agent (`backend/app/agents/recovery.py`)
- **Role**: Automatically analyzes and corrects query errors if an analytical execution fails in DuckDB.
- **Input**: Original user question, dataset profile, failed SQL statement, and sanitized execution error message.
- **Constraint**: Prohibited operations (e.g., security violations) fail immediately without retry. Only syntax, dialect, or type mismatch errors undergo automatic correction (up to 2 retry attempts).
- **Output Schema**: Corrected `SqlProposal`.

### 4. Executive Business Report Agent (`backend/app/agents/planner.py`)
- **Role**: Synthesizes verified tool execution results into actionable business intelligence.
- **Constraint**: Strict factuality — numbers in the report must strictly match the figures present in the verified query result rows.
- **Output Schema**: `BusinessReport` containing:
  - `executive_summary`: High-level business takeaway
  - `key_findings`: Specific metrics and verified data points
  - `business_recommendations`: Actionable steps based on data evidence
  - `data_caveats`: Noted data quality limitations (missing values, refunds, duplicates)

### 5. Orchestration Graph (`backend/app/agents/graph.py`)
- **Framework**: LangGraph `StateGraph(AnalysisState)`.
- **Pipeline**: `START` -> `plan` (generates `AnalysisPlan`) -> `generate_sql` (generates `SqlProposal`) -> `END`.
