# DataFlow — Multi-Agent AI Data Analyst Platform

> Final Year Project · 2025  
> A production-grade AI orchestration platform that autonomously cleans, analyses, visualises, and narrates your data.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  Landing · Dashboard · Upload · Workspace · Timeline    │
│  Visualizations · Report · Trace Viewer · Settings      │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API + SSE
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                         │
│  API Routes → Services → Orchestrator → Agents          │
│  EventBus (SSE) · Storage · PostgreSQL · structlog      │
└──────────────────────┬──────────────────────────────────┘
                       │ LangGraph DAG
┌──────────────────────▼──────────────────────────────────┐
│              Multi-Agent Pipeline                        │
│  Cleaner → Analyst → Visualizer → Storyteller           │
│  (Anthropic Claude API · Tool-use loop · Pydantic I/O)  │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer         | Technology |
|---------------|------------|
| Frontend      | React 18 · TypeScript · Vite · Tailwind CSS |
| State         | Zustand · TanStack Query |
| Charts        | Plotly.js · Recharts |
| Backend       | FastAPI · Python 3.12 |
| Orchestration | LangGraph · Anthropic Claude API |
| Database      | PostgreSQL 16 · SQLAlchemy (async) · Alembic |
| Storage       | Local filesystem (S3/MinIO-ready abstraction) |
| Logging       | structlog (JSON in prod · colour in dev) |

---

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 20+
- PostgreSQL 16 running locally

---

## Quick Start (Windows PowerShell)

### 1. Backend setup

Open a PowerShell terminal:

```powershell
cd fyp-data-analyst\backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Now open .env in Notepad and set:
#   DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/analyst_db
#   ANTHROPIC_API_KEY=sk-ant-your-key-here
#   SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">

# Create the database (run in psql or pgAdmin)
# CREATE DATABASE analyst_db;

# Run migrations
alembic upgrade head

# Start the backend
uvicorn main:app --reload --port 8000
```

### 2. Frontend setup

Open a **second** PowerShell terminal:

```powershell
cd fyp-data-analyst\frontend

npm install

npm run dev
```

Frontend → http://localhost:5173  
Backend API → http://localhost:8000  
API Docs → http://localhost:8000/docs

---

## If PowerShell blocks script execution

Run this once as Administrator:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then re-run `venv\Scripts\Activate.ps1`.

---

## Environment Variables

Copy `backend\.env.example` to `backend\.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Your Anthropic API key (`sk-ant-...`) |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://postgres:pass@localhost:5432/analyst_db` |
| `SECRET_KEY` | ✅ | Run: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `STORAGE_BACKEND` | — | `local` (default) |
| `LLM_MODEL` | — | `claude-opus-4-6` (default) |
| `ENVIRONMENT` | — | `development` |

---

## Project Structure

```
fyp-data-analyst/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base_agent.py           # Abstract BaseAgent + LLM loop
│   │   │   ├── llm_client.py           # Anthropic tool-use client
│   │   │   ├── cleaner/                # Data cleaning agent
│   │   │   ├── analyst/                # EDA + statistical analysis
│   │   │   ├── visualizer/             # Plotly chart generation
│   │   │   └── storyteller/            # Executive narrative + report
│   │   ├── api/v1/
│   │   │   ├── datasets.py             # File upload + CRUD
│   │   │   ├── analysis.py             # Session start / cancel / list
│   │   │   ├── stream.py               # SSE streaming endpoint
│   │   │   ├── reports.py              # Report retrieval
│   │   │   └── agents.py               # Execution trace endpoint
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic settings (env vars)
│   │   │   ├── database.py             # Async SQLAlchemy engine
│   │   │   ├── logging.py              # structlog configuration
│   │   │   ├── middleware.py           # Request ID · logging · CORS
│   │   │   └── exceptions.py           # Typed exception hierarchy
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   ├── orchestration/
│   │   │   ├── graph.py                # LangGraph DAG
│   │   │   ├── runner.py               # Orchestrator runner
│   │   │   ├── state.py                # AnalysisState TypedDict
│   │   │   ├── event_bus.py            # EventBus · SSEQueue · Registry
│   │   │   └── events.py               # Typed workflow events
│   │   ├── processing/
│   │   │   ├── loader.py               # CSV/Excel/JSON/Parquet/PDF parser
│   │   │   └── profiler.py             # Dataset profiling
│   │   ├── prompts/
│   │   │   └── registry.py             # Centralised prompt registry
│   │   ├── schemas/                    # Pydantic v2 API schemas
│   │   ├── services/                   # Business logic layer
│   │   └── storage/                    # Storage abstraction (local/S3)
│   ├── alembic/                        # DB migrations
│   ├── main.py                         # FastAPI app factory
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/                 # AppLayout · Sidebar
│   │   │   └── ui/                     # Button · Card · Badge · Skeleton...
│   │   ├── hooks/                      # useDatasets · useAnalysis · useSSE...
│   │   ├── lib/                        # api.ts · utils.ts
│   │   ├── pages/                      # All 9 pages
│   │   ├── types/                      # TypeScript types
│   │   ├── App.tsx                     # React Router config
│   │   └── main.tsx                    # QueryClient bootstrap
│   ├── tailwind.config.ts
│   └── vite.config.ts
│
├── Makefile
└── SETUP.md
```

---

## The Agent Pipeline

### 1. CleanerAgent
Imputes missing values, fixes data types, handles outliers, normalises columns, computes quality score.

### 2. AnalystAgent
Statistical summary, Pearson correlations, frequency distributions, anomaly detection, trend analysis, group comparisons.

### 3. VisualizerAgent
Selects chart types from analyst recommendations, generates full Plotly figure JSON (bar, histogram, scatter, heatmap, line, box).

### 4. StorytellerAgent
Executive summary, structured narrative blocks, actionable recommendations, dataset health score (A–D), ranked key takeaways.

---

## Real-Time Streaming (SSE)

The frontend connects to `GET /api/v1/stream/{session_id}` via `EventSource`.  
Events flow live during analysis and replay from the database for completed sessions.

Event types: `ANALYSIS_STARTED` · `AGENT_STARTED` · `TOOL_CALLED` · `TOOL_COMPLETED` · `ANALYSIS_PROGRESS` · `INSIGHT_GENERATED` · `CHART_GENERATED` · `AGENT_COMPLETED` · `REPORT_CREATED` · `ANALYSIS_COMPLETED`

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/datasets/upload` | Upload dataset file |
| GET  | `/api/v1/datasets` | List datasets |
| GET  | `/api/v1/datasets/{id}` | Dataset detail + schema |
| POST | `/api/v1/analysis/start` | Start analysis session |
| GET  | `/api/v1/analysis/{id}` | Session detail + agent runs |
| POST | `/api/v1/analysis/{id}/cancel` | Cancel running session |
| GET  | `/api/v1/stream/{session_id}` | SSE stream (live or replay) |
| GET  | `/api/v1/reports/{session_id}` | Full report |
| GET  | `/api/v1/agents/{run_id}/traces` | Execution trace steps |
| GET  | `/api/v1/health` | Health check |

Full interactive docs: http://localhost:8000/docs

---

*Built with FastAPI · LangGraph · Anthropic Claude · React · Tailwind CSS · PostgreSQL*
