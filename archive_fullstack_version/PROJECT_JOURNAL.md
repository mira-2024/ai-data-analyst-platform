# DataFlow AI — Project Journal
### Multi-Agent AI Data Analyst Platform
**Student:** Mira | **Stack:** FastAPI · LangGraph · Gemini · React · TypeScript · PostgreSQL

---

## What Is This Project?

DataFlow AI is a **production-grade SaaS platform** where users upload datasets (CSV, Excel) and a team of autonomous AI agents automatically:

- Cleans and validates the data
- Runs statistical analysis and finds patterns
- Generates professional charts and visualizations
- Writes an executive summary with business recommendations

The key differentiator is **transparency** — users can watch every agent working in real time, see what tools they call, how long each step takes, and why each decision was made. It is not a chatbot. It is an orchestrated multi-agent AI pipeline with a professional frontend.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + TypeScript | Type-safe, component-based UI |
| Styling | TailwindCSS + shadcn/ui | Consistent design system |
| State | Zustand + React Query | Global state + server data caching |
| Charts | Plotly.js | Interactive, professional charts |
| Backend | FastAPI (Python) | Async, fast, auto-docs |
| AI Orchestration | LangGraph | Agent graph with shared state |
| LLM | Google Gemini API (free tier) | No-cost AI reasoning |
| Database | PostgreSQL + SQLAlchemy | Relational, async ORM |
| Migrations | Alembic | DB schema version control |
| Real-time | SSE (Server-Sent Events) | Live agent event streaming |
| Storage | Local filesystem | Dataset file storage |

---

## Architecture Overview

```
Browser (React)
    │
    │  HTTP (REST)          Server-Sent Events (live stream)
    │                       ◄────────────────────────────────
    ▼
FastAPI Backend
    │
    ├── Dataset Service     → stores CSV, profiles schema
    ├── Analysis Service    → creates session, launches background task
    │        │
    │        ▼
    │   LangGraph Orchestrator
    │        │
    │        ├── ① CleanerAgent     → handles missing values, type fixes, outliers
    │        ├── ② AnalystAgent     → correlations, statistics, anomaly detection
    │        ├── ③ VisualizerAgent  → generates Plotly chart configs
    │        └── ④ StorytellerAgent → executive summary + recommendations
    │        
    │   Each agent:
    │     1. Calls Gemini API to reason about the data
    │     2. Uses Python tools (pandas) to do real computation
    │     3. Emits live events → EventBus → SSE → Browser
    │     4. Writes structured output to shared LangGraph state
    │
    └── PostgreSQL
         ├── datasets          (file metadata, schema, quality score)
         ├── analysis_sessions (status, config, token usage)
         ├── agent_runs        (per-agent status, timing, tokens)
         ├── execution_traces  (every tool call recorded)
         └── workflow_events   (full SSE event log for replay)
```

---

## Folder Structure

```
fyp-data-analyst/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base_agent.py         ← shared LLM loop + tool execution
│   │   │   ├── llm_client.py         ← Gemini + Anthropic client (factory)
│   │   │   ├── cleaner/              ← CleanerAgent + tools
│   │   │   ├── analyst/              ← AnalystAgent + tools
│   │   │   ├── visualizer/           ← VisualizerAgent + tools
│   │   │   └── storyteller/          ← StorytellerAgent + tools
│   │   ├── api/v1/
│   │   │   ├── datasets.py           ← upload, list, delete endpoints
│   │   │   ├── analysis.py           ← start, list, get, cancel endpoints
│   │   │   └── stream.py             ← SSE streaming endpoint
│   │   ├── core/
│   │   │   ├── config.py             ← all settings (env vars)
│   │   │   ├── database.py           ← async SQLAlchemy engine + sessions
│   │   │   ├── logging.py            ← structured logging (structlog)
│   │   │   ├── middleware.py         ← CORS, request ID, logging middleware
│   │   │   └── exceptions.py        ← typed HTTP exceptions
│   │   ├── models/                   ← SQLAlchemy ORM models
│   │   ├── orchestration/
│   │   │   ├── event_bus.py          ← per-session pub/sub + SSE queue
│   │   │   ├── events.py             ← all event types (typed Pydantic)
│   │   │   ├── graph.py              ← LangGraph graph builder
│   │   │   ├── runner.py             ← agent node execution wrapper
│   │   │   └── state.py              ← shared TypedDict state
│   │   ├── processing/
│   │   │   ├── loader.py             ← CSV/Excel → DataFrame
│   │   │   └── profiler.py           ← schema detection, quality scoring
│   │   ├── prompts/                  ← centralized prompt registry
│   │   ├── schemas/                  ← Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── analysis_service.py   ← session lifecycle management
│   │   │   ├── dataset_service.py    ← dataset CRUD
│   │   │   └── event_persister.py    ← writes SSE events to DB
│   │   └── storage/                  ← file storage abstraction
│   ├── alembic/                      ← DB migration scripts
│   ├── main.py                       ← FastAPI app factory
│   └── run.py                        ← Windows-safe uvicorn launcher
│
└── frontend/
    └── src/
        ├── components/ui/            ← Button, Card, Badge, Skeleton, etc.
        ├── hooks/
        │   ├── useDatasets.ts        ← dataset CRUD hooks
        │   ├── useAnalysis.ts        ← session hooks + polling
        │   └── useSSE.ts             ← EventSource lifecycle hook
        ├── pages/
        │   ├── LandingPage.tsx
        │   ├── DashboardPage.tsx
        │   ├── UploadPage.tsx
        │   ├── WorkspacePage.tsx     ← dataset detail + schema
        │   ├── AgentTimelinePage.tsx ← MAIN FEATURE: live agent view
        │   ├── VisualizationsPage.tsx
        │   └── ReportPage.tsx
        ├── lib/
        │   ├── api.ts                ← typed fetch wrapper
        │   └── utils.ts              ← formatBytes, timeAgo, etc.
        └── types/                    ← all TypeScript interfaces
```

---

## What We Built — Feature by Feature

### 1. Dataset Upload & Profiling
- User uploads a CSV or Excel file via drag-and-drop
- Backend stores it to disk, creates a DB record
- Profiler runs automatically: detects column types, counts nulls, scores data quality (0–1), identifies datetime and ID columns
- Frontend polls until status changes from `pending` → `ready`
- WorkspacePage shows the full schema table with null %, unique counts, and sample values

### 2. Analysis Session Lifecycle
- User clicks "Run Analysis" → POST /api/v1/analysis/start
- Backend creates an `AnalysisSession` record (status: pending) and one `AgentRun` record per agent
- Immediately commits status to `running` so the frontend sees it
- Launches the LangGraph pipeline as a background asyncio task
- Returns the session immediately — frontend navigates to the timeline

### 3. Multi-Agent Pipeline (LangGraph)
Four agents run **sequentially**, each receiving the previous agent's output:

**CleanerAgent**
- Detects and fills missing values (median for numeric, mode for categorical)
- Fixes column data types
- Detects and flags outliers using IQR
- Normalizes column names
- Outputs: cleaned DataFrame + quality report

**AnalystAgent**
- Reads the cleaned DataFrame
- Calls tools: `statistical_summary`, `correlation_analysis`, `frequency_distribution`, `detect_anomalies`, `group_comparison`, `trend_analysis`
- Outputs: typed list of insights, correlations, anomalies, hypotheses, key statistics

**VisualizerAgent**
- Reads analyst insights + cleaned DataFrame
- Calls tools: `create_bar_chart`, `create_histogram`, `create_scatter_plot`, `create_correlation_heatmap`, `create_line_chart`, `create_box_plot`
- All charts are real Plotly figure dicts computed from actual data
- Outputs: list of PlotlyChartSpec objects ready for frontend rendering

**StorytellerAgent**
- Reads all three previous outputs
- Writes: executive summary, key findings, business recommendations, narrative
- Outputs: structured report with title, sections, and action items

### 4. Real-Time Event Streaming (SSE)
- Every agent step emits a typed event to the `EventBus`
- EventBus fans out to two subscribers: `EventPersister` (writes to DB) and `SSEBroadcaster` (pushes to connected clients)
- Frontend connects an `EventSource` to `/api/v1/stream/{session_id}`
- Timeline page renders each event as it arrives: agent started/completed, tool calls, insights generated, progress bars
- Stream closes gracefully when analysis completes

### 5. Agent Timeline Page
The heart of the platform. Shows:
- Pipeline overview: 4 agent cards with live status badges and progress bars
- Live event log: every event with timestamp, sequence number, and expandable detail
- Auto-scroll to latest event
- Cancel button for running sessions
- Direct navigation to Visualizations and Report when complete

### 6. Visualizations Page
- Renders all Plotly charts generated by VisualizerAgent
- Each chart is interactive (hover, zoom, pan)
- Shows chart title, type, and which columns were used

### 7. Report Page
- Renders the StorytellerAgent's full executive report
- Sections: summary, key insights, recommendations, data quality notes

### 8. Dashboard
- Stats: total datasets, sessions, tokens used
- Recent datasets list with row/column counts
- Recent sessions list with status and duration
- Quick-start CTA when no data exists

---

## Bugs Fixed During Development

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 1 | `ValueError: too many file descriptors` | Windows asyncio `SelectorEventLoop` has 512 FD limit; `--reload` exhausts it | Created `run.py` with `WindowsProactorEventLoopPolicy` (uses IOCP, no FD limit) |
| 2 | `Maximum update depth exceeded` (infinite loop) | `useSSE` had `onComplete`/`onError` callbacks in `useEffect` deps; inline functions get new refs every render → effect re-runs → `setIsConnected(false)` → re-render → loop | Moved callbacks into `useRef` updated via `useLayoutEffect`; removed `setIsConnected` from cleanup |
| 3 | `GET /analysis/{id}` returning 500 | `agent_runs` lazy-loaded relationship accessed during Pydantic serialization outside async context | Added `selectinload(AnalysisSession.agent_runs)` to all queries |
| 4 | `DetachedInstanceError` on dataset | SQLAlchemy object passed to background task became detached when original DB session closed | Changed to pass `dataset_id` (UUID) instead of object; re-fetch inside background task's own session |
| 5 | `MissingGreenlet` on agent_runs | `session.agent_runs` accessed during sync Pydantic validation after async flush | Re-fetch session with `selectinload` before returning from `service.start()` |
| 6 | `EventPersister.__qualname__` AttributeError | EventBus tried `handler.__qualname__` — works for functions, not class instances | Changed to `getattr(handler, "__qualname__", type(handler).__name__)` |
| 7 | `ValueError: truth value of DataFrame is ambiguous` | `state.get("clean_df") or state["raw_df"]` — Python's `or` calls `bool(df)` which pandas refuses | Changed to explicit `if _clean is not None` check in AnalystAgent and VisualizerAgent |
| 8 | Gemini 429 rate limit crashes | Free tier (15 RPM) exceeded when agents fire rapid API calls | Added `_send_with_retry()` to GeminiLLMClient: parses retry-after from error message, waits, retries up to 5× |
| 9 | Session stuck showing `pending` in UI | `_set_session_running` modified DB object but `get_session()` only commits at end of entire long-running background task | Added explicit `await db.commit()` immediately after `_set_session_running` |
| 10 | `status_code=204` with response body | FastAPI newer versions reject 204 responses with body content | Changed dataset delete endpoint to return 200 with `{"deleted": True}` |
| 11 | `@radix-ui/react-badge` 404 on npm | Package does not exist on npm registry | Removed from `package.json` |
| 12 | `ALLOWED_ORIGINS` parse error | pydantic-settings v2 tries JSON-decode on List fields; comma-separated string failed | Set `.env` value as JSON array: `["http://localhost:5173"]` |
| 13 | `add_logger_name` AttributeError | structlog processor tried `.name` on `PrintLogger` which has no such attribute | Removed `stdlib.add_logger_name` from shared_processors |

---

## Current Project Status

| Area | Status |
|---|---|
| Backend API | ✅ Working |
| Database + Migrations | ✅ Working |
| Dataset Upload + Profiling | ✅ Working |
| Analysis Session Lifecycle | ✅ Working |
| LangGraph Orchestration | ✅ Working |
| CleanerAgent | ✅ Working |
| AnalystAgent | ✅ Working |
| VisualizerAgent | ✅ Working |
| StorytellerAgent | ✅ Working |
| SSE Real-time Streaming | ✅ Working |
| Agent Timeline Page | ✅ Working |
| Visualizations Page | ✅ Working |
| Report Page | ✅ Working |
| Dashboard | ✅ Working |
| Gemini API (free tier) | ✅ Working (with rate-limit retry) |
| GitHub Repository | ✅ Pushed |
| Windows compatibility | ✅ Fixed |

**Known limitation:** Gemini free tier allows 15 requests/minute. A full analysis with 4 agents can take 5–15 minutes due to rate-limit waits. This is a free-tier constraint, not a code bug.

---

## What's Left To Do (Future Features)

### High Priority — Core Completeness

**1. ML Predictor Agent (5th Agent)**
Add a `PredictorAgent` that runs after the Analyst:
- Auto-detects the best target column for prediction
- Trains a simple ML model (Random Forest or Linear Regression via scikit-learn)
- Reports feature importance, accuracy, and predictions
- This alone significantly strengthens the Data Science credentials of the FYP

**2. Agent Trace Viewer Page**
The route `/session/{id}/traces/{agentRunId}` exists but the page is not built.
- Show every tool call the agent made, with input/output
- Show the full LLM reasoning chain
- This is the "explainability" feature that makes the platform trustworthy

**3. PDF/Word Report Export**
- Export the StorytellerAgent's report as a downloadable PDF or Word document
- Export charts as PNG images

**4. Chat with Your Data**
- After analysis completes, allow the user to ask follow-up questions
- "Which department has the highest average salary?"
- "What would happen if we removed the outliers?"
- Uses a conversational agent with access to the analysis context

### Medium Priority — Quality of Life

**5. Switch to `google-genai` SDK**
The current `google-generativeai` package is deprecated. The new SDK is `google-genai`.
This is a refactor of `llm_client.py` only — no other files change.

**6. Excel File Support**
Currently only CSV is tested. Add proper Excel `.xlsx` handling in the profiler and loader.

**7. Authentication**
Add user accounts so multiple people can use the platform.
- JWT-based login
- Each user sees only their own datasets and sessions
- Simple email/password is enough for FYP demo

**8. Settings Page**
The Settings page route exists but is empty. Add:
- API key configuration UI
- Default analysis config (which agents to run)
- Model selection (switch between Gemini models)

**9. Dataset Preview Page**
Show the first 50 rows of the dataset in a paginated table so users can inspect their data before running analysis.

**10. Analysis Config Options**
When clicking "Run Analysis", let users choose:
- Which agents to run (toggle each one)
- Focus areas (e.g., "focus on salary analysis")
- Custom questions to answer

### Lower Priority — Polish

**11. Dark/Light Mode Toggle**
Currently hardcoded dark. Add a toggle.

**12. Loading Skeletons**
Some pages flash empty states before data loads. Add proper skeleton loaders.

**13. Error Recovery**
If one agent fails, the others currently still run with degraded input. Add a UI indicator showing which agents succeeded and which failed, and allow re-running failed agents only.

**14. Dataset Versioning**
Allow uploading a new version of the same dataset and comparing analysis results across versions.

---

## How to Run the Project

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16 running locally
- A Gemini API key from https://aistudio.google.com

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Create .env from .env.example and fill in your values
alembic upgrade head           # Run DB migrations
python run.py                  # Start server on port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                    # Start on http://localhost:5173
```

### Environment Variables (backend/.env)
```
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/analyst_db
GEMINI_API_KEY=your_gemini_key_here
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
SECRET_KEY=any_random_32_char_string
```

---

## GitHub Repository

**URL:** https://github.com/mira-2024/ai-data-analyst-platform

---

*Last updated: June 2026*
