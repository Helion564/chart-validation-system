"""
Automated Tests — v3.0.0
=========================
Run with:  pytest tests/ -v --cov=app --cov-report=term-missing

All tests use the `client` fixture provided by conftest.py.
conftest.py handles:
  - Environment variables (API_KEY_ENABLED=false, DEBUG=true)
  - In-memory SQLite DB override
  - Session-scoped TestClient
"""

import pytest
from app.core.config import settings

VALID_HEADERS = {}  # auth disabled via conftest env


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _post(client, payload: dict, headers: dict = None) -> dict:
    response = client.post(
        "/validate-chart", json=payload, headers=headers or VALID_HEADERS
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    return response.json()


# ─── Health ────────────────────────────────────────────────────────────────────


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "3.0.0"


def test_health_detailed(client):
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "uptime_seconds" in data
    assert "database" in data
    assert "python_version" in data


# ─── Metrics ──────────────────────────────────────────────────────────────────


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    for key in ("total_validations", "valid_count", "invalid_count", "average_score"):
        assert key in data


# ─── Auth Tests ───────────────────────────────────────────────────────────────


def test_missing_api_key_returns_401(client):
    """When auth is enabled, missing header → 401."""
    original = settings.API_KEY_ENABLED
    settings.API_KEY_ENABLED = True
    try:
        response = client.post(
            "/validate-chart",
            json={"chart_type": "bar", "data": [1, 2]},
        )
        assert response.status_code == 401
    finally:
        settings.API_KEY_ENABLED = original


def test_wrong_api_key_returns_403(client):
    """Wrong key value → 403."""
    original = settings.API_KEY_ENABLED
    settings.API_KEY_ENABLED = True
    try:
        response = client.post(
            "/validate-chart",
            json={"chart_type": "bar", "data": [1, 2]},
            headers={"X-API-Key": "totally-wrong-key"},
        )
        assert response.status_code == 403
    finally:
        settings.API_KEY_ENABLED = original


# ─── Schema / Response Completeness ───────────────────────────────────────────


def test_response_schema_completeness(client):
    payload = {
        "chart_type": "bar",
        "title": "Q1 Revenue",
        "labels": ["Jan", "Feb", "Mar"],
        "data": [100, 200, 150],
        "objective": "Compare monthly revenue figures",
    }
    data = _post(client, payload)
    assert "score" in data
    assert "status" in data
    assert "issues" in data
    assert "warnings" in data
    assert "recommendations" in data
    breakdown = data["breakdown"]
    for dim in (
        "structure",
        "objective_match",
        "data_quality",
        "visualization_best_practices",
    ):
        assert dim in breakdown
        assert 0 <= breakdown[dim] <= 100


# ─── Input Sanitisation ────────────────────────────────────────────────────────


def test_title_too_long_rejected(client):
    """title > 200 chars → 422."""
    payload = {
        "chart_type": "bar",
        "title": "A" * 201,
        "labels": ["A"],
        "data": [1],
        "objective": "Compare values",
    }
    assert client.post("/validate-chart", json=payload).status_code == 422


def test_objective_too_long_rejected(client):
    """objective > 500 chars → 422."""
    payload = {
        "chart_type": "bar",
        "title": "Test",
        "labels": ["A"],
        "data": [1],
        "objective": "X" * 501,
    }
    assert client.post("/validate-chart", json=payload).status_code == 422


def test_too_many_data_points_rejected(client):
    """data with > 100 items → 422."""
    payload = {
        "chart_type": "bar",
        "title": "Test",
        "labels": [str(i) for i in range(101)],
        "data": list(range(101)),
        "objective": "Compare values",
    }
    assert client.post("/validate-chart", json=payload).status_code == 422


# ─── Valid Charts ──────────────────────────────────────────────────────────────


def test_valid_bar_chart_compare_objective(client):
    payload = {
        "chart_type": "bar",
        "title": "Q1 Revenue Comparison",
        "labels": ["Jan", "Feb", "Mar"],
        "data": [100, 200, 150],
        "objective": "Compare monthly revenue across quarters",
        "dataset_name": "Sales 2025",
    }
    data = _post(client, payload)
    assert data["status"] == "valid"
    assert data["score"] >= 70


def test_valid_line_chart_trend_objective(client):
    payload = {
        "chart_type": "line",
        "title": "Revenue Growth Trend",
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "data": [100, 120, 150, 180],
        "objective": "Show revenue trend over time",
    }
    data = _post(client, payload)
    assert data["status"] == "valid"
    assert data["breakdown"]["objective_match"] >= 70


def test_valid_histogram_distribution_objective(client):
    payload = {
        "chart_type": "histogram",
        "title": "Score Distribution",
        "labels": ["0-20", "20-40", "40-60", "60-80", "80-100"],
        "data": [5, 10, 30, 40, 15],
        "objective": "Show distribution of student scores",
    }
    data = _post(client, payload)
    assert data["status"] == "valid"


def test_valid_pie_chart_proportion_objective(client):
    payload = {
        "chart_type": "pie",
        "title": "Market Share Breakdown",
        "labels": ["Product A", "Product B", "Product C"],
        "data": [40, 35, 25],
        "objective": "Show proportion of market share by product",
    }
    data = _post(client, payload)
    assert data["status"] == "valid"


# ─── Objective Mismatch ────────────────────────────────────────────────────────


def test_objective_type_mismatch_trend_with_pie(client):
    payload = {
        "chart_type": "pie",
        "title": "Monthly Trend",
        "labels": ["Jan", "Feb", "Mar"],
        "data": [100, 200, 150],
        "objective": "Show monthly revenue trend over time",
    }
    data = _post(client, payload)
    assert data["breakdown"]["objective_match"] < 70
    assert any("trend" in i.lower() or "line" in i.lower() for i in data["issues"])


def test_objective_type_mismatch_compare_with_histogram(client):
    payload = {
        "chart_type": "histogram",
        "title": "Sales Comparison",
        "labels": ["A", "B", "C"],
        "data": [10, 20, 30],
        "objective": "Compare product sales figures",
    }
    data = _post(client, payload)
    assert data["breakdown"]["objective_match"] < 70


# ─── Missing Fields ────────────────────────────────────────────────────────────


def test_missing_data_field(client):
    payload = {
        "chart_type": "line",
        "title": "Empty Chart",
        "labels": ["A", "B"],
        "objective": "Show a trend",
    }
    data = _post(client, payload)
    assert data["breakdown"]["structure"] < 70
    assert any("data" in i.lower() for i in data["issues"])


def test_missing_objective(client):
    payload = {
        "chart_type": "bar",
        "title": "Sales Chart",
        "labels": ["Jan", "Feb"],
        "data": [100, 200],
    }
    data = _post(client, payload)
    assert data["breakdown"]["objective_match"] < 70
    assert any("objective" in i.lower() for i in data["issues"])


def test_missing_title_deduction(client):
    payload = {
        "chart_type": "line",
        "labels": ["Q1", "Q2"],
        "data": [50, 75],
        "objective": "Compare quarterly revenue trend",
    }
    data = _post(client, payload)
    assert any("title" in i.lower() for i in data["issues"])


# ─── Invalid Chart Type ────────────────────────────────────────────────────────


def test_invalid_chart_type(client):
    payload = {
        "chart_type": "radar",
        "title": "Unsupported Type",
        "labels": ["X"],
        "data": [10],
        "objective": "Compare values",
    }
    data = _post(client, payload)
    assert any(
        "chart type" in i.lower() or "unsupported" in i.lower() for i in data["issues"]
    )


# ─── Data Consistency ─────────────────────────────────────────────────────────


def test_data_label_mismatch(client):
    payload = {
        "chart_type": "pie",
        "title": "Mismatch Test",
        "labels": ["A", "B"],
        "data": [10, 20, 30],
        "objective": "Show proportions",
    }
    data = _post(client, payload)
    assert any("mismatch" in i.lower() for i in data["issues"])


def test_non_numeric_data(client):
    payload = {
        "chart_type": "bar",
        "title": "Bad Data",
        "labels": ["A", "B"],
        "data": [10, "not_a_number"],
        "objective": "Compare values",
    }
    data = _post(client, payload)
    assert data["breakdown"]["data_quality"] < 70
    assert any(
        "non-numeric" in i.lower() or "numeric" in i.lower() for i in data["issues"]
    )


# ─── Empty Payload ─────────────────────────────────────────────────────────────


def test_empty_payload_returns_400(client):
    assert client.post("/validate-chart", json={}).status_code == 400


# ─── Viz Best Practices ────────────────────────────────────────────────────────


def test_pie_chart_too_many_slices(client):
    payload = {
        "chart_type": "pie",
        "title": "Too Many Slices",
        "labels": [f"Cat{i}" for i in range(10)],
        "data": [10] * 10,
        "objective": "Show proportion of categories",
    }
    data = _post(client, payload)
    assert data["breakdown"]["visualization_best_practices"] < 100
    assert any("slice" in i.lower() or "pie" in i.lower() for i in data["issues"])


# ─── Axis Validation ──────────────────────────────────────────────────────────


def test_invalid_y_axis_range(client):
    payload = {
        "chart_type": "bar",
        "title": "Broken Axis",
        "labels": ["A", "B"],
        "data": [10, 20],
        "objective": "Compare values",
        "y_axis": {"min": 100, "max": 50},
    }
    data = _post(client, payload)
    assert any("axis" in i.lower() for i in data["issues"])


# ─── Recommendations ──────────────────────────────────────────────────────────


def test_recommendations_present_on_issues(client):
    payload = {
        "chart_type": "pie",
        "title": "Revenue Trend Over Time",
        "labels": ["Jan", "Feb", "Mar"],
        "data": [100, 200, 150],
        "objective": "Show revenue trend over time",
    }
    data = _post(client, payload)
    if data["issues"]:
        assert len(data["recommendations"]) > 0


# ─── All-Zero Data ─────────────────────────────────────────────────────────────


def test_all_zero_data_warning(client):
    payload = {
        "chart_type": "bar",
        "title": "Zero Data",
        "labels": ["A", "B", "C"],
        "data": [0, 0, 0],
        "objective": "Compare values",
    }
    data = _post(client, payload)
    assert any("zero" in w.lower() for w in data["warnings"])


# ─── Batch Validation ──────────────────────────────────────────────────────────


def test_batch_validation_success(client):
    charts = [
        {
            "chart_type": "bar",
            "title": "Chart 1",
            "labels": ["A", "B"],
            "data": [10, 20],
            "objective": "Compare values",
        },
        {
            "chart_type": "line",
            "title": "Chart 2",
            "labels": ["Q1", "Q2", "Q3"],
            "data": [100, 150, 200],
            "objective": "Show revenue trend",
        },
    ]
    response = client.post("/validate-chart/batch", json=charts)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    for result in results:
        assert "score" in result
        assert "breakdown" in result
        assert "status" in result


def test_batch_empty_returns_400(client):
    assert client.post("/validate-chart/batch", json=[]).status_code == 400


def test_batch_over_limit_returns_400(client):
    charts = [{"chart_type": "bar", "data": [1]} for _ in range(21)]
    assert client.post("/validate-chart/batch", json=charts).status_code == 400


# ─── History Endpoint ──────────────────────────────────────────────────────────


def test_history_endpoint_returns_paginated_response(client):
    """POST a chart then verify /history reflects it."""
    _post(
        client,
        {
            "chart_type": "bar",
            "title": "History Test",
            "labels": ["A", "B"],
            "data": [10, 20],
            "objective": "Compare values",
        },
    )
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "records" in data
    assert "page" in data
    assert data["total"] >= 1


def test_history_filter_by_status(client):
    response = client.get("/history?status=valid")
    assert response.status_code == 200
    for record in response.json()["records"]:
        assert record["status"] == "valid"


def test_history_filter_by_chart_type(client):
    _post(
        client,
        {
            "chart_type": "line",
            "title": "Filter Test",
            "labels": ["Q1", "Q2"],
            "data": [10, 20],
            "objective": "Show trend over time",
        },
    )
    response = client.get("/history?chart_type=line")
    assert response.status_code == 200
    for record in response.json()["records"]:
        assert record["chart_type"] == "line"


def test_history_pagination(client):
    response = client.get("/history?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) <= 5
    assert data["page"] == 1
    assert data["page_size"] == 5


# ─── Metrics Persist Across Calls ─────────────────────────────────────────────


def test_metrics_reflect_db(client):
    """After submitting a chart, metrics total_validations must increment."""
    before = client.get("/metrics").json()["total_validations"]
    _post(
        client,
        {
            "chart_type": "bar",
            "title": "Metrics Test",
            "labels": ["A"],
            "data": [1],
            "objective": "Compare values",
        },
    )
    after = client.get("/metrics").json()["total_validations"]
    assert after == before + 1


# ─── Response Headers ─────────────────────────────────────────────────────────


def test_correlation_id_header_present(client):
    response = client.get("/")
    assert "x-correlation-id" in response.headers
    assert "x-response-time" in response.headers


def test_custom_correlation_id_echoed(client):
    response = client.get("/", headers={"X-Correlation-ID": "test-abc-123"})
    assert response.headers.get("x-correlation-id") == "test-abc-123"
