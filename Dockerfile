# ============================================================
# Dockerfile — Chart Validation System v3.1.0
# Multi-stage: node-builder + python-builder -> slim runtime
# Non-root user & hardened security (CIS compliance)
# ============================================================

# ── Stage 1: Frontend Builder ────────────────────────────────
FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /build-frontend
COPY frontend/package*.json ./
RUN npm clean-install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Builder ──────────────────────────────────
FROM python:3.11-slim-bookworm AS python-builder
WORKDIR /build-python
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 3: Runtime ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

# Patch OS vulnerabilities (standard hardening)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# OCI image labels
LABEL org.opencontainers.image.title="Chart Validation System" \
      org.opencontainers.image.description="DevSecOps-integrated chart validation API" \
      org.opencontainers.image.version="3.1.0" \
      org.opencontainers.image.authors="nageshbhagelli" \
      org.opencontainers.image.source="https://github.com/nageshbhagelli/chart-validation-system" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy Python packages
COPY --from=python-builder /install /usr/local

# Copy application source (backend only)
COPY app/ ./app/

# Copy ONLY the compiled frontend (no package.json or node_modules)
# This prevents Trivy from scanning dev dependencies in production
COPY --from=frontend-builder /build-frontend/dist ./frontend/dist

# Create a non-root user
RUN addgroup --gid 1001 --system appgroup \
    && adduser --uid 1001 --system --ingroup appgroup --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appgroup /app

USER appuser
EXPOSE 8000

# Container health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()"

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log"]
