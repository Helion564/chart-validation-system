"""
API Routes — v3.0.0
====================
All HTTP endpoints for the Chart Validation System.

Gaps closed vs v2:
  - API key auth enforced on /validate-chart and /history
  - Rate limiting via slowapi (30/min single, 10/min batch)
  - /validate-chart persists every result to SQLite via SQLAlchemy
  - /metrics reads REAL counts from the database (survives restarts)
  - /history endpoint: paginated, filterable validation log
  - /validate-chart/batch also persisted
"""

import json
import platform
import sys
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_api_key
from app.models.db_models import ValidationHistory
from app.models.schemas import (
    ChartData,
    HealthResponse,
    HistoryRecord,
    HistoryResponse,
    MetricsResponse,
    ValidationResult,
)
from app.services.validation_engine import validate_chart
from app.utils.helpers import timestamp_now

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Router ────────────────────────────────────────────────────────────────────
router = APIRouter(tags=["Chart Validation"])

# Track app start time for uptime calculation
_START_TIME = time.time()


# ── Helper: persist result ─────────────────────────────────────────────────────


async def _persist(
    chart: ChartData, result: ValidationResult, db: AsyncSession
) -> None:
    """Write one ValidationHistory row to the database."""
    record = ValidationHistory(
        chart_type=chart.chart_type,
        title=chart.title,
        objective=chart.objective,
        dataset_name=chart.dataset_name,
        label_count=len(chart.labels) if chart.labels else None,
        data_point_count=len(chart.data) if chart.data else None,
        score=result.score,
        status=result.status,
        structure_score=result.breakdown.structure,
        objective_match_score=result.breakdown.objective_match,
        data_quality_score=result.breakdown.data_quality,
        viz_score=result.breakdown.visualization_best_practices,
        issues_json=json.dumps(result.issues),
        warnings_json=json.dumps(result.warnings),
        recommendations_json=json.dumps(result.recommendations),
    )
    db.add(record)
    # commit is handled by the get_db() dependency


# ── Health ────────────────────────────────────────────────────────────────────


@router.get("/", response_model=HealthResponse, summary="Health Check")
async def root() -> HealthResponse:
    """Liveness probe — suitable for Docker/Kubernetes."""
    return HealthResponse(
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        status="healthy",
        message=(
            "Chart Validation API v3 is running. "
            "Visit /docs for Swagger UI or /dashboard for the web dashboard."
        ),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ── Single Validation ─────────────────────────────────────────────────────────

@router.get("/health/detailed", summary="Detailed Health Check")
async def health_detailed(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe — includes DB connectivity check."""
    db_ok = True
    try:
        await db.execute(select(func.count()).select_from(ValidationHistory))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "python_version": sys.version,
        "platform": platform.platform(),
        "debug_mode": settings.DEBUG,
        "database": "ok" if db_ok else "unreachable",
        "timestamp": timestamp_now(),
    }


# ── Metrics (real, from DB) ────────────────────────────────────────────────────


@router.get("/metrics", response_model=MetricsResponse, summary="Live Metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> MetricsResponse:
    """
    Returns real validation statistics from the database.
    Survives server restarts — always reflects the full history.
    """
    total_result = await db.execute(
        select(func.count()).select_from(ValidationHistory)
    )
    total: int = total_result.scalar_one()

    valid_result = await db.execute(
        select(func.count()).where(ValidationHistory.status == "valid")
    )
    valid_count: int = valid_result.scalar_one()

    avg_result = await db.execute(select(func.avg(ValidationHistory.score)))
    avg_score: float = round(avg_result.scalar_one() or 0.0, 2)

    return MetricsResponse(
        total_validations=total,
        valid_count=valid_count,
        invalid_count=total - valid_count,
        average_score=avg_score,
        uptime_seconds=round(time.time() - _START_TIME, 2),
    )


# ── Single Validation ─────────────────────────────────────────────────────────


@router.post(
    "/validate-chart",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate a Single Chart",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(settings.RATE_LIMIT)
async def validate_chart_endpoint(
    request: Request,
    chart: ChartData,
    db: AsyncSession = Depends(get_db),
) -> ValidationResult:
    """
    POST /validate-chart — requires X-API-Key header.
    Rate limited to 30 requests/minute per IP.
    Result is persisted to the database.
    """
    if all(
        v is None
        for v in [chart.chart_type, chart.title, chart.labels, chart.data, chart.objective]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is empty. Provide at least one chart field.",
        )

    result = validate_chart(chart)
    await _persist(chart, result, db)
    return result


# ── Batch Validation ──────────────────────────────────────────────────────────


@router.post(
    "/validate-chart/batch",
    response_model=List[ValidationResult],
    status_code=status.HTTP_200_OK,
    summary="Validate Multiple Charts (Batch)",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(settings.RATE_LIMIT_BATCH)
async def validate_chart_batch(
    request: Request,
    charts: List[ChartData],
    db: AsyncSession = Depends(get_db),
) -> List[ValidationResult]:
    """
    POST /validate-chart/batch — requires X-API-Key header.
    Rate limited to 10 requests/minute per IP.
    All results are persisted to the database.
    """
    if not charts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch request must contain at least 1 chart.",
        )
    if len(charts) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch limit is 20 charts. Received {len(charts)}.",
        )

    results: List[ValidationResult] = []
    for chart in charts:
        result = validate_chart(chart)
        await _persist(chart, result, db)
        results.append(result)

    return results


# ── History ────────────────────────────────────────────────────────────────────


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Validation History (Paginated)",
    dependencies=[Depends(require_api_key)],
)
async def get_history(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(20, ge=1, le=100, description="Records per page."),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by 'valid' or 'invalid'."
    ),
    chart_type_filter: Optional[str] = Query(
        None, alias="chart_type", description="Filter by chart type."
    ),
) -> HistoryResponse:
    """
    GET /history — paginated, filterable log of all past validations.
    Requires X-API-Key header.
    """
    query = select(ValidationHistory).order_by(ValidationHistory.created_at.desc())

    if status_filter in ("valid", "invalid"):
        query = query.where(ValidationHistory.status == status_filter)
    if chart_type_filter:
        query = query.where(ValidationHistory.chart_type == chart_type_filter)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    # Paginated records
    offset = (page - 1) * page_size
    paginated_q = query.offset(offset).limit(page_size)
    rows = (await db.execute(paginated_q)).scalars().all()

    records = [
        HistoryRecord(
            id=r.id,
            chart_type=r.chart_type,
            title=r.title,
            objective=r.objective,
            score=r.score,
            status=r.status,
            structure_score=r.structure_score,
            objective_match_score=r.objective_match_score,
            data_quality_score=r.data_quality_score,
            viz_score=r.viz_score,
            issues=r.issues,
            warnings=r.warnings,
            recommendations=r.recommendations,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return HistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        records=records,
    )
