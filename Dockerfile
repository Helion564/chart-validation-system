# ============================================================
# Dockerfile — Chart Validation System v3.2.0 (Hardened Alpine)
# Multi-stage: node-builder + alpine-builder -> alpine runtime
# Minimal attack surface to pass strict security scans
# ============================================================

# ── Stage 1: Frontend Builder (Node) ────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /build-frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Builder (Alpine) ────────────────────────
FROM python:3.11-alpine AS python-builder
WORKDIR /build-python

# Install build dependencies for C-extensions (bcrypt, etc.)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    make

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 3: Runtime (Alpine) ────────────────────────────────
FROM python:3.11-alpine AS runtime

# Patch OS vulnerabilities (standard hardening)
RUN apk update && apk upgrade --no-cache

WORKDIR /app

# Copy Python packages from builder
COPY --from=python-builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Copy compiled frontend
COPY --from=frontend-builder /build-frontend/dist ./frontend/dist

# Create a non-root user (Alpine use addgroup/adduser)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chown -R appuser:appgroup /app

USER appuser
EXPOSE 8000

# Container health check (Alpine needs wget or curl installed, but we can use python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()"

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log"]
