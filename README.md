<div align="center">

# 📊 Chart Validation & Objective Compliance System

### *Does your chart actually say what you think it says?*

[![CI/CD Pipeline](https://github.com/nageshbhagelli/chart-validation-system/actions/workflows/main.yml/badge.svg)](https://github.com/nageshbhagelli/chart-validation-system/actions/workflows/main.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Coverage](https://img.shields.io/badge/Coverage-86%25-4CAF50?logo=codecov&logoColor=white)](https://codecov.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com)
[![Security: Trivy](https://img.shields.io/badge/Security-Trivy%20%2B%20Bandit-orange)](https://github.com/aquasecurity/trivy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**A production-grade DevSecOps API that validates charts against their stated objectives — detecting misleading visuals before they reach your audience.**

[📖 API Docs](http://localhost:8000/docs) · [🖥️ Dashboard](http://localhost:8000/dashboard) · [📊 Metrics](http://localhost:8000/metrics)

</div>

---

## The Problem This Solves

Tools like Tableau and Power BI are great at *generating* charts. None of them validate whether the chart is **correct for the data's intent**.

Common failures this system catches:
- 📉 Using a **pie chart** to show a *trend* (should be line chart)
- 📊 Using a **histogram** to *compare* categories (should be bar chart)
- ⚠️ Y-axis starting at 50 instead of 0 — **visually inflating differences**
- 🔢 **Non-numeric data** quietly accepted into a data series
- 🍕 Pie charts with **12 slices** — unreadable by any standard
- 📭 Charts with **no stated objective** — you can't evaluate what it's for

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│         Dashboard (Chart.js)  ·  Swagger UI  ·  curl / SDK     │
└─────────────────────┬───────────────────────────────────────────┘
                      │  X-API-Key  +  JSON payload
┌─────────────────────▼───────────────────────────────────────────┐
│                    FASTAPI APPLICATION                          │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │  Rate Limiter│  │  Auth Middleware │  │  Request Timing  │   │
│  │ (slowapi)    │  │  (X-API-Key)    │  │  + Correlation   │   │
│  └──────┬───────┘  └────────┬────────┘  └────────┬─────────┘   │
│         └──────────────────▼──────────────────────┘            │
│                    VALIDATION ENGINE                            │
│  ┌─────────────┐ ┌──────────────────┐ ┌──────────────────────┐ │
│  │  Structure  │ │ Objective Match  │ │    Data Quality      │ │
│  │    (30%)    │ │  NLP Keywords    │ │ IQR Outliers + Axis  │ │
│  │             │ │     (35%)        │ │       (20%)          │ │
│  └─────────────┘ └──────────────────┘ └──────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Viz Best Practices (15%)                          ││
│  │     Slice count · Baseline · Min points                     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      │  Persist every result
┌─────────────────────▼───────────────────────────────────────────┐
│                   SQLite DATABASE                               │
│          validation_history table · /metrics · /history        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

| Category | Feature |
|----------|---------|
| 🧠 **Intelligence** | 4-dimension weighted scoring engine |
| 🧠 **Intelligence** | 30+ NLP keyword→chart-type mappings (`trend`→line, `compare`→bar, `distribution`→histogram, `proportion`→pie) |
| 🧠 **Intelligence** | IQR-based outlier detection flags suspicious data points |
| 🧠 **Intelligence** | Axis range sanity — catches inverted or truncated scales |
| 🔐 **Security** | `X-API-Key` auth with `secrets.compare_digest` (timing-attack safe) |
| 🔐 **Security** | `SecretStr` — keys never appear in logs or stack traces |
| 🔐 **Security** | Hard exit on startup if default secrets used in production |
| 🔐 **Security** | `max_length` + `max_items` on all inputs — no oversized payloads |
| ⚡ **Performance** | Rate limiting: 30/min (single), 10/min (batch) per IP |
| ⚡ **Performance** | Async SQLAlchemy 2.0 — non-blocking DB I/O |
| 📦 **Ops** | Persistent history — `/metrics` survives server restarts |
| 📦 **Ops** | `/history` endpoint — paginated, filterable validation log |
| 📦 **Ops** | Correlation ID + response time on every request header |
| 🐳 **Docker** | Multi-stage build · non-root user · HEALTHCHECK |
| 🚀 **CI/CD** | 8-job GitHub Actions pipeline (lint → trivy → SBOM → GHCR) |
| 🖥️ **UI** | Dark-mode dashboard with animated score gauge + Chart.js preview |

---

## Scoring System

Every chart is scored across **4 weighted dimensions**, producing a 0–100 aggregate:

```
Final Score = (Structure × 0.30) + (Objective Match × 0.35)
            + (Data Quality × 0.20) + (Viz Best Practices × 0.15)
```

| Dimension | Weight | Checks |
|-----------|:------:|--------|
| **Structure** | 30% | Data present, chart_type valid, labels match data length |
| **Objective Match** | 35% | NLP keyword alignment, title reflects objective, type suitability |
| **Data Quality** | 20% | All values numeric, IQR outliers, axis min < max, no all-zero arrays |
| **Viz Best Practices** | 15% | Pie slices ≤ 7, bar baseline, scatter min 3 points, histogram buckets |

> **Score ≥ 70** → `valid` &nbsp;&nbsp;|&nbsp;&nbsp; **Score < 70** → `invalid`

### *Does your chart actually say what you think it says?*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Security: Bandit](https://img.shields.io/badge/Security-Bandit-orange)](https://github.com/PyCQA/bandit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## API Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|:----:|:----------:|-------------|
| `GET` | `/` | — | — | Liveness probe |
| `GET` | `/health/detailed` | — | — | Readiness probe + DB connectivity |
| `GET` | `/metrics` | — | — | Real-time stats (from DB, restarts-safe) |
| `POST` | `/validate-chart` | ✅ | 30/min | Validate a single chart |
| `POST` | `/validate-chart/batch` | ✅ | 10/min | Validate up to 20 charts |
| `GET` | `/history` | ✅ | — | Paginated validation log |
| `GET` | `/docs` | — | — | Swagger UI |
| `GET` | `/redoc` | — | — | ReDoc docs |
| `GET` | `/dashboard` | — | — | Web dashboard |

---

## Quick Start

### 1 · Local Development

```bash
git clone https://github.com/nageshbhagelli/chart-validation-system.git
cd chart-validation-system

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets (required)
cp .env.example .env
```

Edit `.env` and set your secrets:

```bash
# Generate strong keys
python -c "import secrets; print(secrets.token_hex(32))"
```

```env
SECRET_KEY=<generated-key>
API_KEY=<generated-key>
DEBUG=true
```

```bash
# Run with hot-reload
uvicorn app.main:app --reload
```

| URL | What |
|-----|------|
| http://localhost:8000/dashboard | Web dashboard |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/metrics | Live metrics |

### 2 · Docker

```bash
# One command — builds and starts
make compose-up

# Or manually
docker build -t chart-validation-system .
docker run -d -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e API_KEY=your-api-key \
  chart-validation-system
```

---

## Usage Examples

### ✅ Valid Chart (Perfect Score)

```bash
curl -s -X POST http://localhost:8000/validate-chart \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "chart_type": "bar",
    "title": "Q1 2025 Regional Revenue",
    "labels": ["North", "South", "East", "West"],
    "data": [450000, 380000, 520000, 290000],
    "objective": "Compare regional revenue figures for Q1 2025",
    "dataset_name": "Sales Report 2025"
  }'
```

```json
{
  "score": 100,
  "status": "valid",
  "breakdown": {
    "structure": 100,
    "objective_match": 100,
    "data_quality": 100,
    "visualization_best_practices": 100
  },
  "issues": [],
  "warnings": ["Chart type 'bar' aligns well with objective keyword(s): compare."],
  "recommendations": []
}
```

### 4. Default Credentials
| Username | Password | Role |
|----------|----------|------|
| `admin` | `password123` | **Administrator** |
| `user` | `password123` | **Standard User** |

---

### ❌ Wrong Chart Type — Objective Mismatch

```bash
curl -s -X POST http://localhost:8000/validate-chart \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "chart_type": "pie",
    "title": "Revenue Trend 2025",
    "labels": ["Jan", "Feb", "Mar", "Apr"],
    "data": [100, 150, 200, 175],
    "objective": "Show monthly revenue trend over time"
  }'
```

```json
{
  "score": 54,
  "status": "invalid",
  "breakdown": {
    "structure": 90,
    "objective_match": 40,
    "data_quality": 100,
    "visualization_best_practices": 100
  },
  "issues": [
    "Chart type 'pie' does not match the stated objective (keywords: trend). Recommended type(s): line, area."
  ],
  "warnings": [],
  "recommendations": [
    "Change chart type to 'line' to better communicate the 'trend' intent."
  ]
}
```

---

### 📦 Batch Validation

```bash
curl -s -X POST http://localhost:8000/validate-chart/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '[
    { "chart_type": "line", "title": "Revenue Trend", "labels": ["Q1","Q2","Q3"], "data": [100,150,200], "objective": "Show growth trend" },
    { "chart_type": "pie",  "title": "Market Share",  "labels": ["A","B","C"],    "data": [40,35,25],    "objective": "Show proportion of market share" }
  ]'
```

Returns an array of `ValidationResult` objects — one per chart.

---

### 📜 Validation History

```bash
# Last 5 invalid bar charts
curl -s "http://localhost:8000/history?status=invalid&chart_type=bar&page=1&page_size=5" \
  -H "X-API-Key: your-api-key"
```

```json
{
  "total": 12,
  "page": 1,
  "page_size": 5,
  "records": [
    {
      "id": 42,
      "chart_type": "bar",
      "title": "Sales Chart",
      "score": 55,
      "status": "invalid",
      "structure_score": 100,
      "objective_match_score": 40,
      "created_at": "2025-05-03T16:41:00Z",
      ...
    }
  ]
}
```

---

## Environment Variables

| Variable | Default | Prod Required | Description |
|----------|---------|:-------------:|-------------|
| `SECRET_KEY` | `change-me-in-production` | ✅ **Yes** | App secret. **Server refuses to start with default in production.** |
| `API_KEY` | `dev-key-change-me` | ✅ **Yes** | API authentication key. **Server refuses to start with default in production.** |
| `API_KEY_ENABLED` | `true` | — | Set `false` in test/CI environments |
| `DEBUG` | `false` | — | Enables SQL query logging; relaxes startup guard |
| `LOG_LEVEL` | `INFO` | — | `DEBUG` · `INFO` · `WARNING` · `ERROR` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./chart_validation.db` | — | Any SQLAlchemy async URL (e.g. PostgreSQL) |
| `VALID_SCORE_THRESHOLD` | `70` | — | Minimum score for `valid` verdict |
| `RATE_LIMIT` | `30/minute` | — | Per-IP rate limit for single validation |
| `RATE_LIMIT_BATCH` | `10/minute` | — | Per-IP rate limit for batch validation |

> **Security note:** The app calls `sys.exit(1)` at startup if `SECRET_KEY` or `API_KEY` are still defaults and `DEBUG=false`. This makes misconfigured production deployments impossible to run silently.

---

## DevSecOps Pipeline

Every push and pull request to `main` triggers an 8-job pipeline:

```
push / PR  ──►  main
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
   [lint]             [sast]              [dependency-scan]
   flake8 + black     Bandit SAST         Safety v3 CVE check
   (auto-format       (fail on HIGH)      (pip packages)
    then verify)
       │
       ▼
   [test]
   pytest + coverage ≥80%
   Newman API integration tests
       │
       ▼
   [docker-build]
   Build image
   Smoke test container (health + validate-chart)
       │
       ├──────────────────────────────────┐
       ▼                                  ▼
   [trivy-scan]                       [sbom]
   CVE scan on image                  Syft → SPDX JSON
   SARIF → GitHub Security tab        attached as artifact
       │
       ▼ (main branch only)
   [publish]
   Push to ghcr.io
   SLSA provenance attestation
   SBOM attached to image manifest
```

**Security artifacts produced per run:**
- `bandit-report.json` — SAST findings
- `trivy-results.sarif` — CVE results (visible in GitHub Security tab)
- `sbom.spdx.json` — Full software bill of materials

---

## Testing

```bash
# Run all tests with coverage report
make test

# Run directly
pytest tests/ -v --cov=app --cov-report=term-missing
```

**Current status:** `36 passed · 86% coverage · 0 warnings`

### Test Categories

| Category | Tests |
|----------|-------|
| Health endpoints | `/`, `/health/detailed` |
| Metrics (DB-backed) | Counter increment verification |
| Auth enforcement | 401 (missing key), 403 (wrong key) |
| Input sanitisation | max_length on strings, max_items on lists → 422 |
| Valid chart scenarios | bar+compare, line+trend, histogram+distribution, pie+proportion |
| Objective mismatch | pie+trend, histogram+compare |
| Missing fields | data, objective, title |
| Data quality | non-numeric, all-zero, label mismatch |
| Axis validation | inverted y-axis range |
| Viz best practices | pie >7 slices |
| Batch endpoint | success, empty→400, >20→400 |
| History endpoint | pagination, status filter, chart_type filter |
| Response headers | X-Correlation-ID echo, X-Response-Time |

---

## Project Structure

```
chart-validation-system/
│
├── .github/
│   └── workflows/main.yml          ← 8-job DevSecOps CI/CD pipeline
│
├── app/
│   ├── api/
│   │   └── routes.py               ← All endpoints + rate limiter + DB writes
│   ├── core/
│   │   ├── config.py               ← Settings with SecretStr + startup guard
│   │   ├── database.py             ← Async SQLAlchemy 2.0 engine + session
│   │   └── security.py             ← X-API-Key dependency (timing-safe)
│   ├── models/
│   │   ├── schemas.py              ← Pydantic v2 schemas (input-sanitised)
│   │   └── db_models.py            ← SQLAlchemy ORM (ValidationHistory)
│   ├── services/
│   │   └── validation_engine.py    ← 4-dimension scoring engine + NLP
│   ├── utils/
│   │   └── helpers.py
│   └── main.py                     ← App factory + middleware + lifespan
│
├── frontend/
│   └── index.html                  ← Dark dashboard (Chart.js + SVG gauge)
│
├── tests/
│   ├── conftest.py                 ← In-memory DB override + session fixture
│   └── test_validation.py          ← 36 tests
│
├── Dockerfile                      ← Multi-stage · non-root user · HEALTHCHECK
├── docker-compose.yml              ← Local stack with health checks
├── Makefile                        ← dev · test · build · trivy · compose-up
├── requirements.txt
├── pytest.ini
├── .bandit                         ← Bandit config (known false-positive skip)
└── .env.example                    ← Safe template (no real secrets)
```

---

## Makefile Commands

```bash
make dev            # Run with hot-reload
make test           # pytest + coverage ≥80%
make lint           # flake8
make format         # black (in-place)
make sast           # Bandit SAST scan
make dep-scan       # Safety dependency scan
make security-scan  # sast + dep-scan
make build          # Docker build
make compose-up     # docker-compose up --build -d
make trivy          # Trivy CVE scan on built image
make clean          # Remove __pycache__, coverage files
```

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
Built with FastAPI · SQLAlchemy · Docker · GitHub Actions · Trivy · Bandit · slowapi
</div>
