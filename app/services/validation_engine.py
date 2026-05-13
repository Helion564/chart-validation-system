"""
Validation Engine — Rule-Based + Objective-Aware
=================================================
Core business logic that evaluates chart data across four quality dimensions:

  1. structure             — data presence, type validity, label consistency
  2. objective_match       — NLP keyword mapping to recommended chart types
  3. data_quality          — numeric integrity, outlier detection, axis sanity
  4. visualization_best_practices — title, label count, zero-baseline warnings

Each dimension is scored 0-100 and weighted to produce the final aggregate.
Rules return structured RuleResult objects; no business logic in routes.py.

Weights (must sum to 1.0):
  structure                 : 0.30
  objective_match           : 0.35
  data_quality              : 0.20
  visualization_best_practices : 0.15
"""

import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.schemas import ChartData, ScoreBreakdown, ValidationResult

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

DIMENSION_WEIGHTS: Dict[str, float] = {
    "structure": 0.30,
    "objective_match": 0.35,
    "data_quality": 0.20,
    "visualization_best_practices": 0.15,
}

# NLP keyword → recommended chart types mapping
# Keys are lowercase keywords; values are sets of valid chart_types
OBJECTIVE_KEYWORD_MAP: Dict[str, List[str]] = {
    # Trend / time-series
    "trend":       ["line", "area"],
    "over time":   ["line", "area"],
    "growth":      ["line", "bar"],
    "progress":    ["line", "bar"],
    "timeline":    ["line"],
    "time series": ["line"],
    "forecast":    ["line"],
    "projection":  ["line"],
    # Comparison
    "compare":     ["bar", "grouped bar"],
    "comparison":  ["bar", "grouped bar"],
    "contrast":    ["bar", "grouped bar"],
    "rank":        ["bar"],
    "ranking":     ["bar"],
    "versus":      ["bar", "scatter"],
    "vs":          ["bar", "scatter"],
    # Distribution
    "distribution": ["histogram", "box"],
    "spread":       ["histogram", "scatter"],
    "frequency":    ["histogram", "bar"],
    "range":        ["histogram", "box"],
    "variability":  ["histogram", "scatter"],
    # Proportion / part-of-whole
    "proportion":  ["pie", "donut"],
    "percentage":  ["pie", "donut", "bar"],
    "share":       ["pie", "donut"],
    "breakdown":   ["pie", "bar"],
    "composition": ["pie", "bar"],
    "part of":     ["pie"],
    # Correlation / relationship
    "correlation": ["scatter"],
    "relationship": ["scatter", "line"],
    "scatter":     ["scatter"],
    "cluster":     ["scatter"],
}

# ─── Internal Data Classes ───────────────────────────────────────────────────


@dataclass
class DimensionResult:
    """Result of evaluating a single scoring dimension."""

    score: int                          # 0-100
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# ─── Dimension 1: Structure ──────────────────────────────────────────────────


def _score_structure(chart: ChartData) -> DimensionResult:
    """
    Evaluate structural completeness of the chart payload.

    Checks:
      - Data presence (critical — 40 pts)
      - chart_type validity (30 pts)
      - labels existence (20 pts)
      - data-label length match (10 pts)
    """
    issues: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    penalty = 0

    # Rule S1 — data must be present
    if not chart.data:
        penalty += 40
        issues.append(
            "Missing or empty 'data' field — no data points to validate."
        )
        recommendations.append(
            "Provide a non-empty 'data' array with numeric values."
        )
    elif len(chart.data) < settings.MIN_DATA_POINTS:
        penalty += 20
        issues.append(
            f"Insufficient data: {len(chart.data)} point(s) provided, "
            f"minimum is {settings.MIN_DATA_POINTS}."
        )

    # Rule S2 — chart_type must be valid
    if not chart.chart_type:
        penalty += 30
        issues.append("Missing 'chart_type' field.")
        recommendations.append(
            f"Set 'chart_type' to one of: "
            f"{', '.join(settings.ALLOWED_CHART_TYPES)}."
        )
    elif chart.chart_type.lower() not in settings.ALLOWED_CHART_TYPES:
        penalty += 30
        allowed = ", ".join(settings.ALLOWED_CHART_TYPES)
        issues.append(
            f"Unsupported chart type '{chart.chart_type}'. "
            f"Allowed: {allowed}."
        )
        recommendations.append(
            f"Change 'chart_type' to one of the supported types: {allowed}."
        )

    # Rule S3 — labels should be present
    if not chart.labels:
        penalty += 20
        issues.append("Missing or empty 'labels' field.")
        recommendations.append(
            "Provide category labels matching the length of your data array."
        )

    # Rule S4 — data-label length match
    if chart.data and chart.labels and len(chart.data) != len(chart.labels):
        penalty += 10
        issues.append(
            f"Data-label length mismatch: {len(chart.data)} data point(s) "
            f"vs {len(chart.labels)} label(s)."
        )
        recommendations.append(
            "Ensure 'data' and 'labels' arrays have the same number of elements."
        )

    # Rule S5 — multi-series consistency (warn only)
    if chart.multi_series and chart.labels:
        for name, values in chart.multi_series.items():
            if len(values) != len(chart.labels):
                warnings.append(
                    f"Multi-series '{name}' has {len(values)} values "
                    f"but {len(chart.labels)} labels are defined."
                )

    score = max(0, 100 - penalty)
    return DimensionResult(
        score=score,
        issues=issues,
        warnings=warnings,
        recommendations=recommendations,
    )


# ─── Dimension 2: Objective Match ────────────────────────────────────────────


def _score_objective_match(chart: ChartData) -> DimensionResult:
    """
    Evaluate how well the chart type aligns with the stated objective.

    Uses a keyword-to-chart-type mapping for NLP-lite semantic analysis.
    """
    issues: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    penalty = 0

    # Rule O1 — objective must be present
    if not chart.objective or not chart.objective.strip():
        penalty += 40
        issues.append(
            "Missing 'objective' field — chart purpose is unclear."
        )
        recommendations.append(
            "State the chart's purpose (e.g., 'Compare monthly revenue across regions')."
        )
        return DimensionResult(
            score=max(0, 100 - penalty),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
        )

    objective_lower = chart.objective.lower()
    chart_type_lower = (chart.chart_type or "").lower()

    # Find matched keywords and their recommended chart types
    matched_chart_types: List[str] = []
    matched_keywords: List[str] = []
    for keyword, valid_types in OBJECTIVE_KEYWORD_MAP.items():
        if keyword in objective_lower:
            matched_keywords.append(keyword)
            matched_chart_types.extend(valid_types)

    # Rule O2 — check alignment
    if matched_keywords and chart_type_lower:
        if chart_type_lower not in matched_chart_types:
            penalty += 50
            recommended = list(dict.fromkeys(matched_chart_types))  # dedupe
            issues.append(
                f"Chart type '{chart.chart_type}' does not match the stated "
                f"objective (keywords: {', '.join(matched_keywords)}). "
                f"Recommended type(s): {', '.join(recommended)}."
            )
            recommendations.append(
                f"Change chart type to '{recommended[0]}' to better "
                f"communicate the '{matched_keywords[0]}' intent."
            )
        else:
            # Bonus: strong alignment
            warnings.append(
                f"Chart type '{chart.chart_type}' aligns well with "
                f"objective keyword(s): {', '.join(matched_keywords)}."
            )
    elif not matched_keywords and chart_type_lower:
        # No keywords found — mild warning, not an error
        warnings.append(
            "Objective does not contain recognized visualization keywords. "
            "Consider adding intent words like 'compare', 'trend', 'distribution'."
        )
        penalty += 10  # small penalty for vague objectives

    # Rule O3 — title should reflect the objective
    if chart.title and chart.objective:
        title_words = set(chart.title.lower().split())
        obj_words = set(chart.objective.lower().split())
        overlap = title_words & obj_words
        if len(overlap) < 1:
            warnings.append(
                "Title does not share words with the objective — "
                "they may be misaligned."
            )
            recommendations.append(
                "Align your chart title with the stated objective "
                "for better readability."
            )

    # Rule O4 — title presence contributes to objective clarity
    if not chart.title or not chart.title.strip():
        penalty += 10
        issues.append(
            "Missing 'title' — charts need a descriptive title to "
            "communicate their purpose."
        )
        recommendations.append(
            "Add a concise title that summarises what the chart shows."
        )

    score = max(0, 100 - penalty)
    return DimensionResult(
        score=score,
        issues=issues,
        warnings=warnings,
        recommendations=recommendations,
    )


# ─── Dimension 3: Data Quality ───────────────────────────────────────────────


def _score_data_quality(chart: ChartData) -> DimensionResult:
    """
    Evaluate numeric integrity, outlier presence, and axis sanity.

    Checks:
      - All values numeric (40 pts)
      - No None/NaN values (20 pts)
      - Outlier detection via IQR (20 pts — warn only)
      - Axis range sanity (20 pts)
    """
    issues: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    penalty = 0

    numeric_values: List[float] = []

    # Rule D1 — all values must be numeric
    if chart.data:
        non_numeric_indices: List[int] = []
        for idx, val in enumerate(chart.data):
            if val is None:
                non_numeric_indices.append(idx)
            elif not isinstance(val, (int, float)):
                try:
                    numeric_values.append(float(val))
                except (TypeError, ValueError):
                    non_numeric_indices.append(idx)
            elif isinstance(val, float) and (val != val):  # NaN check
                non_numeric_indices.append(idx)
            else:
                numeric_values.append(float(val))

        if non_numeric_indices:
            penalty += 40
            issues.append(
                f"Non-numeric or null value(s) at index(es) "
                f"{non_numeric_indices}. All data values must be numeric."
            )
            recommendations.append(
                "Replace null or string values with numeric data. "
                "Use 0 if a value is intentionally absent."
            )

    # Rule D2 — outlier detection (IQR method, warn-only)
    if len(numeric_values) >= 4:
        try:
            q1 = statistics.quantiles(numeric_values, n=4)[0]
            q3 = statistics.quantiles(numeric_values, n=4)[2]
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outlier_indices = [
                i for i, v in enumerate(numeric_values)
                if v < lower_fence or v > upper_fence
            ]
            if outlier_indices:
                outlier_vals = [round(numeric_values[i], 2) for i in outlier_indices]
                warnings.append(
                    f"Potential outlier(s) detected at position(s) "
                    f"{outlier_indices}: values {outlier_vals}. "
                    "Verify these are not data entry errors."
                )
                recommendations.append(
                    "Review outlier data points — they may distort the "
                    "visual scale and mislead viewers."
                )
        except statistics.StatisticsError:
            pass  # Not enough distinct values for quantiles

    # Rule D3 — axis range sanity
    if chart.y_axis:
        if (
            chart.y_axis.min is not None
            and chart.y_axis.max is not None
            and chart.y_axis.min >= chart.y_axis.max
        ):
            penalty += 20
            issues.append(
                f"Y-axis range is invalid: min ({chart.y_axis.min}) must be "
                f"less than max ({chart.y_axis.max})."
            )
            recommendations.append(
                "Set y_axis.min strictly less than y_axis.max."
            )
        elif numeric_values and chart.y_axis.min is not None:
            data_min = min(numeric_values)
            if chart.y_axis.min > data_min:
                warnings.append(
                    f"Y-axis minimum ({chart.y_axis.min}) is greater than "
                    f"the smallest data value ({data_min:.2f}). "
                    "This may truncate the chart and mislead viewers."
                )
                recommendations.append(
                    "Set y_axis.min to 0 or lower than your smallest data value "
                    "to avoid a misleading truncated axis."
                )

    if chart.x_axis:
        if (
            chart.x_axis.min is not None
            and chart.x_axis.max is not None
            and chart.x_axis.min >= chart.x_axis.max
        ):
            penalty += 20
            issues.append(
                f"X-axis range is invalid: min ({chart.x_axis.min}) must be "
                f"less than max ({chart.x_axis.max})."
            )
            recommendations.append(
                "Set x_axis.min strictly less than x_axis.max."
            )

    # Rule D4 — all-zero data warning
    if numeric_values and all(v == 0 for v in numeric_values):
        warnings.append(
            "All data values are zero — this chart will display no meaningful information."
        )
        penalty += 10
        recommendations.append(
            "Ensure your data contains non-zero values before visualising."
        )

    score = max(0, 100 - penalty)
    return DimensionResult(
        score=score,
        issues=issues,
        warnings=warnings,
        recommendations=recommendations,
    )


# ─── Dimension 4: Visualization Best Practices ───────────────────────────────


def _score_viz_best_practices(chart: ChartData) -> DimensionResult:
    """
    Evaluate adherence to data visualization design standards.

    Checks:
      - Label count (too many labels on a pie chart is unreadable)
      - Pie chart with many slices
      - Zero-baseline requirement for bar charts
      - Dataset attribution
    """
    issues: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    penalty = 0

    chart_type = (chart.chart_type or "").lower()
    label_count = len(chart.labels) if chart.labels else 0

    # Rule V1 — pie charts with > 7 slices are unreadable
    if chart_type == "pie" and label_count > 7:
        penalty += 30
        issues.append(
            f"Pie chart has {label_count} slices — more than 7 slices "
            "make a pie chart very hard to read."
        )
        recommendations.append(
            "Limit pie charts to 7 or fewer slices. "
            "Group smaller categories into 'Other'."
        )

    # Rule V2 — pie charts with a single slice are meaningless
    if chart_type == "pie" and label_count == 1:
        warnings.append(
            "Pie chart has only 1 slice — consider using a different chart type."
        )
        recommendations.append(
            "A single-value pie chart conveys no comparative information. "
            "Use a KPI tile or single number instead."
        )

    # Rule V3 — too many data points on a bar chart
    if chart_type == "bar" and label_count > 20:
        warnings.append(
            f"Bar chart has {label_count} bars — consider grouping or "
            "using a horizontal bar chart for readability."
        )
        recommendations.append(
            "Limit bar charts to 20 bars. "
            "Sort bars by value for easier comparison."
        )

    # Rule V4 — bar/line charts should start at zero
    if chart_type in ("bar", "line") and chart.y_axis:
        y_min = chart.y_axis.min
        if y_min is not None and y_min != 0 and y_min > 0:
            warnings.append(
                f"Y-axis minimum is {y_min} — non-zero baselines on bar/line "
                "charts can be misleading."
            )
            recommendations.append(
                "Set y_axis.min to 0 for bar and line charts to avoid "
                "visually distorting differences."
            )

    # Rule V5 — scatter charts need at least 3 data points to show any pattern
    if chart_type == "scatter" and label_count < 3:
        warnings.append(
            "Scatter charts should have at least 3 data points to reveal patterns."
        )
        recommendations.append(
            "Add more data points to your scatter chart for meaningful correlation analysis."
        )

    # Rule V6 — histogram with very few buckets
    if chart_type == "histogram" and label_count < 5:
        warnings.append(
            f"Histogram has only {label_count} bucket(s) — "
            "consider increasing to 5-20 for a useful distribution view."
        )

    # Rule V7 — dataset attribution (informational)
    if not chart.dataset_name:
        recommendations.append(
            "Add a 'dataset_name' field to indicate the source of your data "
            "for better traceability and trustworthiness."
        )

    score = max(0, 100 - penalty)
    return DimensionResult(
        score=score,
        issues=issues,
        warnings=warnings,
        recommendations=recommendations,
    )


# ─── Aggregate Engine ────────────────────────────────────────────────────────


def validate_chart(chart: ChartData) -> ValidationResult:
    """
    Run the full 4-dimension validation pipeline against the supplied chart data.

    Returns a ``ValidationResult`` containing:
    - score       : weighted aggregate (0-100)
    - breakdown   : per-dimension ScoreBreakdown
    - issues      : blocking problems that must be fixed
    - warnings    : non-blocking observations
    - recommendations : actionable improvement suggestions
    - status      : 'valid' if score >= threshold, else 'invalid'

    Logging:
        Each call logs at INFO level with chart_type, objective (truncated),
        final score, and status.
    """
    # Evaluate all four dimensions
    structure_result = _score_structure(chart)
    objective_result = _score_objective_match(chart)
    data_quality_result = _score_data_quality(chart)
    viz_result = _score_viz_best_practices(chart)

    # Weighted aggregate score
    raw_score = (
        structure_result.score * DIMENSION_WEIGHTS["structure"]
        + objective_result.score * DIMENSION_WEIGHTS["objective_match"]
        + data_quality_result.score * DIMENSION_WEIGHTS["data_quality"]
        + viz_result.score * DIMENSION_WEIGHTS["visualization_best_practices"]
    )
    aggregate_score = max(0, min(100, round(raw_score)))

    # Merge outputs
    all_issues = (
        structure_result.issues
        + objective_result.issues
        + data_quality_result.issues
        + viz_result.issues
    )
    all_warnings = (
        structure_result.warnings
        + objective_result.warnings
        + data_quality_result.warnings
        + viz_result.warnings
    )
    # Deduplicate while preserving order
    all_recommendations = list(
        dict.fromkeys(
            structure_result.recommendations
            + objective_result.recommendations
            + data_quality_result.recommendations
            + viz_result.recommendations
        )
    )

    status = "valid" if aggregate_score >= settings.VALID_SCORE_THRESHOLD else "invalid"

    logger.info(
        "Chart validated | type=%s | objective='%s' | score=%d | status=%s",
        chart.chart_type,
        (chart.objective or "")[:60],
        aggregate_score,
        status,
    )

    return ValidationResult(
        score=aggregate_score,
        breakdown=ScoreBreakdown(
            structure=structure_result.score,
            objective_match=objective_result.score,
            data_quality=data_quality_result.score,
            visualization_best_practices=viz_result.score,
        ),
        issues=all_issues,
        warnings=all_warnings,
        recommendations=all_recommendations,
        status=status,
    )
