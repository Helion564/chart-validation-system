# ============================================================
# Dockerfile — Chart Validation System v2.0.0
# Multi-stage build: builder + slim runtime
# Non-root user for security (CIS Benchmark compliance)
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
# To pin to an exact digest (recommended for production), replace the line below with:
#   FROM python:3.11-slim@sha256:<digest> AS builder
# Get the current digest with: docker inspect python:3.11-slim --format='{{index .RepoDigests 0}}'
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a prefix we can copy
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

# Patch OS vulnerabilities (standard hardening)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# OCI image labels
LABEL org.opencontainers.image.title="Chart Validation System" \
      org.opencontainers.image.description="DevSecOps-integrated chart validation API" \
      org.opencontainers.image.version="3.0.0" \
      org.opencontainers.image.authors="nageshbhagelli" \
      org.opencontainers.image.source="https://github.com/nageshbhagelli/chart-validation-system" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/
COPY frontend/ ./frontend/

# Create a non-root user (Debian slim: use addgroup/adduser)
RUN addgroup --gid 1001 --system appgroup \
    && adduser --uid 1001 --system --ingroup appgroup --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Expose the application port
EXPOSE 8000

# Container health check — Docker/Kubernetes liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()"

# Default command — production-grade Uvicorn settings
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log"]
