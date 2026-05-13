"""
Pydantic Schemas (Data Models)
===============================
v3.0.0 — Input sanitisation hardening:
  - max_length constraints on all string fields (prevents abuse)
  - max_items constraints on lists (prevents giant payloads)
  - min/max on numeric fields
  - HistoryRecord and HistoryResponse for the /history endpoint
"""

from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, List, Optional
from datetime import datetime

# ─── Request Schemas ─────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[str] = Field("user", max_length=20)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class AxisRange(BaseModel):
    """Optional axis configuration for validation of scale integrity."""

    min: Optional[float] = Field(None, description="Minimum axis value.")
    max: Optional[float] = Field(None, description="Maximum axis value.")
    label: Optional[str] = Field(
        None, max_length=100, description="Axis label (e.g., 'Revenue (USD)')."
    )

# ─── Request Schemas ─────────────────────────────────────────────────────────


class AxisRange(BaseModel):
    """Optional axis configuration for validation of scale integrity."""

    min: Optional[float] = Field(None, description="Minimum axis value.")
    max: Optional[float] = Field(None, description="Maximum axis value.")
    label: Optional[str] = Field(
        None, max_length=100, description="Axis label (e.g., 'Revenue (USD)')."
    )


class ChartData(BaseModel):
    """
    Incoming chart payload sent by the client.

    All string fields have max_length to prevent payload abuse.
    All list fields have max_items to cap memory usage.
    """

    chart_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of chart (bar, line, pie, scatter, histogram).",
        examples=["bar", "line", "pie"],
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Title / heading of the chart.",
        examples=["Quarterly Revenue"],
    )
    labels: Optional[List[str]] = Field(
        None,
        max_length=100,  # max 100 labels
        description="Category labels for each data point.",
        examples=[["Jan", "Feb", "Mar"]],
    )
    data: Optional[List[Any]] = Field(
        None,
        max_length=100,  # max 100 data points
        description="Numeric data values corresponding to each label.",
        examples=[[100, 200, 150]],
    )
    objective: Optional[str] = Field(
        None,
        max_length=500,
        description="The stated objective / purpose of the chart.",
        examples=["Compare monthly sales across quarters"],
    )
    x_axis: Optional[AxisRange] = Field(
        None,
        description="X-axis configuration for scale validation.",
    )
    y_axis: Optional[AxisRange] = Field(
        None,
        description="Y-axis configuration for scale validation.",
    )
    dataset_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Name or source of the dataset being visualized.",
        examples=["Q1 2025 Sales Data"],
    )
    multi_series: Optional[Dict[str, List[Any]]] = Field(
        None,
        description=(
            "Optional multi-series data. Keys are series names, "
            "values are numeric arrays matching the labels length."
        ),
        examples=[{"Series A": [10, 20], "Series B": [30, 40]}],
    )

    @model_validator(mode="after")
    def validate_multi_series_length(self) -> "ChartData":
        """Ensure each multi_series array matches the labels length."""
        if self.multi_series and self.labels:
            label_len = len(self.labels)
            for series_name, values in self.multi_series.items():
                if len(values) != label_len:
                    raise ValueError(
                        f"Multi-series '{series_name}' has {len(values)} values "
                        f"but {label_len} labels are defined."
                    )
        return self


# ─── Response Schemas ────────────────────────────────────────────────────────


class ScoreBreakdown(BaseModel):
    """Granular per-dimension score breakdown (each 0-100)."""

    structure: int = Field(..., ge=0, le=100)
    objective_match: int = Field(..., ge=0, le=100)
    data_quality: int = Field(..., ge=0, le=100)
    visualization_best_practices: int = Field(..., ge=0, le=100)


class ValidationResult(BaseModel):
    """Full response returned after chart validation."""

    score: int = Field(..., ge=0, le=100, description="Weighted aggregate score.")
    breakdown: ScoreBreakdown = Field(..., description="Per-dimension scores.")
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    status: str = Field(..., description="'valid' or 'invalid'.")


class HealthResponse(BaseModel):
    """Root health-check response."""

    app: str
    version: str
    status: str
    message: str


class MetricsResponse(BaseModel):
    """Real-time metrics from the database."""

    total_validations: int
    valid_count: int
    invalid_count: int
    average_score: float
    uptime_seconds: float


# ─── History Schemas ─────────────────────────────────────────────────────────


class HistoryRecord(BaseModel):
    """Single validation history entry returned from /history."""

    id: int
    chart_type: Optional[str]
    title: Optional[str]
    objective: Optional[str]
    score: int
    status: str
    structure_score: int
    objective_match_score: int
    data_quality_score: int
    viz_score: int
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Paginated history list."""

    total: int
    page: int
    page_size: int
    records: List[HistoryRecord]
