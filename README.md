# DataFlow AI — A Multi-Agent System for Automated Data Science

**Final Year Project — B.Sc. Data Science, Lebanese University**
**Student:** Mira

[![CI](https://github.com/mira-2024/ai-data-analyst-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mira-2024/ai-data-analyst-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC)

---

## 1. Abstract

DataFlow AI is an automated data-science pipeline. A user uploads a tabular
dataset (CSV / Excel / JSON) and a coordinated team of specialised agents
performs a complete analytical workflow: **data preparation → exploratory data
analysis → inferential statistics → supervised machine learning → reporting.**

The system is deliberately **computation-first**. Every statistic, hypothesis
test and model metric is computed with established scientific libraries
(`pandas`, `NumPy`, `SciPy`, `scikit-learn`) and is fully reproducible. A Large
Language Model (Google Gemini) is used **only as an optional narration layer**
that translates the already-computed numbers into readable prose — it never
generates the numbers themselves. This separation is the core methodological
choice of the project: the data science is real and verifiable, and the LLM is
a convenience, not the source of truth.

## 2. Problem Statement

Standard exploratory analysis and baseline modelling involve a repetitive
sequence of steps (profiling, cleaning, testing, modelling, reporting) that a
practitioner repeats for almost every new dataset. DataFlow AI automates this
baseline workflow while keeping the methodology transparent, so that the analyst
can start from a rigorous, reproducible first pass instead of a blank notebook.

## 3. System Architecture

```
                ┌──────────────────────────────────────────────┐
                │              Streamlit interface              │
                │   Data Preview · EDA · Modeling · Chat tabs    │
                └───────────────────────┬──────────────────────┘
                                        │
                                ┌───────▼────────┐
                                │  Orchestrator  │  intent routing
                                └───────┬────────┘
        ┌──────────────┬───────────────┼───────────────┬───────────────┐
        ▼              ▼               ▼               ▼               ▼
   CleaningAgent  AnalysisAgent   ModelingAgent  VisualizationAgent  ReportAgent
        │              │               │               │               │
        └──────────────┴───────────────┴───────────────┴───────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │   ml/  (data-science core) │
                          │  eda · statistics · modeling
                          │  pandas · SciPy · scikit-learn
                          └────────────────────────────┘
```

The `ml/` package is the scientific engine and has **no dependency on any
language model**. The `agents/` are thin orchestration wrappers around it.

## 4. The Data-Science Core (`ml/`)

| Module | Responsibility | Methods |
|---|---|---|
| `ml/eda.py` | Exploratory Data Analysis | dataset profiling, descriptive statistics (incl. skewness, excess kurtosis, coefficient of variation), categorical entropy, missing-value analysis, IQR + z-score outlier detection, correlation matrices |
| `ml/statistics.py` | Inferential statistics | Shapiro-Wilk / D'Agostino normality tests, Pearson & Spearman correlation significance, Welch's t-test, one-way ANOVA, chi-square test of independence (with Cramér's V), automatic feature-vs-target screening |
| `ml/modeling.py` | Supervised machine learning | automatic task detection, leakage-safe preprocessing pipeline, cross-validated training of Logistic/Linear Regression, Random Forest and Gradient Boosting, held-out evaluation, permutation feature importance |

See `docs/METHODOLOGY.md` for the full statistical and modelling methodology.

## 5. The Agents (`agents/`)

| Agent | What it does |
|---|---|
| **CleaningAgent** | Deterministic, audited data preparation: deduplication, median/mode imputation, whitespace trimming. Returns a transparent change log. |
| **AnalysisAgent** | Runs the EDA + significance tests in `ml/` and reports the real numbers; optionally adds an LLM interpretation grounded in those numbers. |
| **ModelingAgent** | Runs the scikit-learn pipeline, builds model-comparison / feature-importance / confusion-matrix charts, and interprets the metrics. |
| **VisualizationAgent** | Generates EDA charts (rule-based, or LLM-proposed when a key is present). |
| **ReportAgent** | Assembles a reproducible report from computed statistics + optional executive summary. |
| **ChatAgent** | Free-form Q&A (requires an LLM). |

## 6. Running the Project

### Prerequisites
- Python 3.10+

### Install & run
```bash
cd Mira_Fyp
python -m venv venv
venv\Scripts\activate            # Windows  (use: source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (default http://localhost:8501), then click
**Load Sample Data** in the sidebar, or upload your own file.

### Optional: enable the Chat tab and LLM narration
The **EDA** and **Modeling** tabs work with no configuration. To enable the
Chat tab and the natural-language interpretations, create a file named `.env`
in the project root (see `.env.example`):
```
GEMINI_API_KEY=your_key_from_https://aistudio.google.com/apikey
LLM_MODEL=gemini-2.5-flash
```

## 7. Testing

The data-science core, the cleaning agent and the orchestrator are covered by an
automated `pytest` suite (`tests/`). It checks the statistics and ML outputs,
guards against regressions (e.g. the cleaning agent must not turn missing
categories into the string `"nan"`; continuous numeric features must not be
mistaken for ID columns), and verifies the pipeline is reproducible.

```bash
pip install -r requirements-dev.txt
pytest                       # 26 tests
pytest --cov=ml --cov=agents # with coverage
```

Tests run automatically on every push via GitHub Actions (`.github/workflows/ci.yml`)
across Python 3.10–3.12.

## 8. Reproducibility

All randomised steps (train/test splitting, model training, permutation
importance) use a fixed seed (`random_state=42`), so results are identical
across runs. No result depends on a network call to an LLM.

## 9. Repository Layout

```
Mira_Fyp/
├── app.py                      Streamlit entry point (4 tabs)
├── ml/                         DATA-SCIENCE