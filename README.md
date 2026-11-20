# InsightPilot AI — Autonomous Data Analyst

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![DuckDB](https://img.shields.io/badge/Analytics-DuckDB-FFF000.svg?style=flat&logo=duckdb)](https://duckdb.org)
[![NVIDIA NIM](https://img.shields.io/badge/AI-NVIDIA%20NIM%20%26%20Gemini-76B900.svg?style=flat&logo=nvidia)](https://developer.nvidia.com)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com)

**InsightPilot AI** is a full-stack autonomous business intelligence application that transforms raw CSV datasets into verified answers, interactive charts, and evidence-backed executive reports in seconds.

Users simply drop any CSV file, explore an automatically generated dataset dashboard, and ask natural-language business questions. InsightPilot formulates multi-step analytical plans, generates safe SQL queries, executes them inside an isolated DuckDB engine, and synthesizes clear, factual answers with zero mathematical hallucinations.

---

## 🌟 Key Features

- **Upload-First Experience**: Clean drag-and-drop CSV onboarding with schema detection, row bounding, and recent dataset resume trays.
- **Intelligent Dataset Dashboard**: Instantly generates deterministic KPIs (Net Revenue, Unique Orders, Units Sold, Average Order Value, and Exception/Return rates) and date coverage ranges directly in DuckDB without LLM hallucinations.
- **Natural Language Data Analyst**: Ask complex analytical questions in plain English (e.g., *"What are the top 3 categories by revenue?"*, *"How did monthly sales trend throughout 2025?"*).
- **Multi-Provider AI Architecture**: Native support for **NVIDIA NIM API** (`nvidia/nemotron-3.5-bolt-e4b`) and **Google Gemini** (`gemini-3.5-flash`) with automatic cascading multi-model fallback.
- **Strict Execution Separation & Security**:
  - Treats all dataset values as untrusted data.
  - SQLGlot AST validation enforces read-only `SELECT` queries against the controlled `dataset` view.
  - Strictly forbids DDL/DML (`DROP`, `DELETE`, `INSERT`, `UPDATE`), filesystem calls (`read_csv`), extensions, and external database connections.
- **Self-Healing Error Recovery**: If DuckDB execution encounters a syntax or column binder error, the recovery agent diagnoses the error and automatically corrects the query on retry.
- **Interactive Recharts Visuals**: Dynamic Line and Bar charts for time-series trends and category comparisons with custom tooltips and responsive sizing.
- **Plain-English Methodology**: Replaces raw developer logs with an expandable *"How this was calculated"* explanation of metrics, filters, and policies, with an optional technical audit view for SQL inspection.
- **Context-Aware Multi-Turn Follow-Ups**: Ask natural follow-up questions (e.g., *"Show the monthly trend for this"*, *"Compare with top category"*) reusing previous analysis context.
- **One-Click Report Export**: Download executive summaries, key findings, recommendations, and calculation traces as Markdown reports.

---

## 🏗️ Architecture & Workflow

```
[ Upload CSV ] 
      │
      ▼
[ Pandas Profiler + DuckDB ] ──► [ Automatic Intelligent Dashboard ]
      │                                    │
      ▼                                    ▼
[ Natural Language Question ] ─────► [ AI Planner (NVIDIA / Gemini) ]
                                           │
                                           ▼
                                [ Safe SQL Proposal ]
                                           │
                                           ▼
                               [ AST Security Validator ]
                                           │
                                           ▼
                                [ Read-Only DuckDB Engine ]
                                           │
                                           ▼
                           [ Report Synthesizer & Visualizer ]
                                           │
                                           ▼
                                [ Direct Verified Answer ]
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Recharts, Lucide Icons, Tailwind CSS |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy |
| **Analytical Engine** | DuckDB (In-process columnar SQL engine), Pandas, NumPy |
| **AI / LLMs** | NVIDIA NIM API (`meta/llama-3.3-70b`, `nvidia/nemotron-3.5-bolt-e4b`), Google Gemini (`gemini-3.5-flash`), LangGraph |
| **Security & AST** | SQLGlot (AST parsing & allowlist validation) |
| **Testing** | Pytest, FastAPI TestClient, Vite Build Verification |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11 or newer**
- **Node.js 20 or newer**
- An **NVIDIA NIM API key** or **Gemini API key**

---

### 1. Clone & Configure

```bash
git clone https://github.com/Manikantareddie/Autoanlaysis.git
cd Autoanlaysis
```

Copy the example environment configuration:

```bash
# Windows (PowerShell)
Copy-Item .env.example backend/.env
Copy-Item .env.example .env

# Linux / macOS
cp .env.example backend/.env
cp .env.example .env
```

Open `backend/.env` and insert your API key:

```ini
# LLM Provider: 'nvidia' or 'gemini'
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=nvidia/nemotron-3.5-bolt-e4b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Gemini Fallback (Optional)
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-3.5-flash
```

---

### 2. Backend Setup & Startup

Create and activate a virtual environment, then install dependencies:

```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Start the FastAPI backend server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

- **Backend API:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/health`

---

### 3. Frontend Setup & Startup

In a second terminal, install dependencies and start the Vite dev server:

```powershell
cd frontend
npm install
npm run dev
```

- **Application URL:** `http://localhost:5173`

---

## 🧪 Testing & Verification

Run the full backend test suite (unit tests, DuckDB integration, SQL validator, data profiler):

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

Verify frontend TypeScript types and production build:

```powershell
cd frontend
npm run build
```

---

## 🔒 Security & Safe Execution Boundary

1. **Untrusted Data Boundary**: Dataset values and user prompts are strictly isolated. Data is never passed as prompt instructions.
2. **Read-Only SQL AST**: Every query is parsed into an Abstract Syntax Tree (AST) via SQLGlot before execution. Any operation outside of allowlisted analytical functions is rejected with `403 Forbidden`.
3. **DuckDB Isolation**: Queries execute against a strictly read-only DuckDB connection with strict thread and memory limits (256MB).
4. **Credential Safety**: API keys are loaded server-side only via environment variables and are never exposed to the frontend or version control.

---

## 📄 License

This project is licensed under the MIT License.
