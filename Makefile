# ============================================================
# Makefile — Chart Validation System v2.0.0
# Simplifies common dev/ops tasks into short commands
# ============================================================

APP_NAME       := chart-validation-system
IMAGE_NAME     := chart-validation-system
IMAGE_TAG      := latest
CONTAINER_NAME := chart-validation-api
PORT           := 8000

.PHONY: help install run dev test lint format security-scan \
        build docker-run docker-stop docker-logs clean

# ── Help ────────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Local Development ────────────────────────────────────────
install: ## Install Python dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

run: ## Run the API with uvicorn (production mode)
	python -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

dev: ## Run with hot-reload (development)
	python -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload

# ── Testing ──────────────────────────────────────────────────
test: ## Run pytest with coverage report
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

test-ci: ## Run tests with XML coverage (for CI)
	pytest tests/ -v --cov=app --cov-report=xml --cov-fail-under=80

# ── Code Quality ─────────────────────────────────────────────
lint: ## Run flake8 linter
	flake8 app/ tests/ --count --max-line-length=100 --statistics

format: ## Format code with black
	black app/ tests/

format-check: ## Check formatting without modifying files
	black app/ tests/ --check

# ── Security ─────────────────────────────────────────────────
sast: ## Run Bandit SAST scan
	bandit -r app/ -ll --format screen

dep-scan: ## Run Safety dependency vulnerability scan
	safety scan

security-scan: sast dep-scan ## Run all security scans

# ── Docker ───────────────────────────────────────────────────
build: ## Build the Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run: build ## Build and run the container
	docker run -d \
	  --name $(CONTAINER_NAME) \
	  -p $(PORT):$(PORT) \
	  --restart unless-stopped \
	  $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Container started. API available at http://localhost:$(PORT)"

docker-stop: ## Stop and remove the container
	docker stop $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME)

docker-logs: ## Tail container logs
	docker logs -f $(CONTAINER_NAME)

compose-up: ## Start full stack with docker-compose
	docker-compose up -d --build

compose-down: ## Stop docker-compose stack
	docker-compose down

compose-logs: ## Tail docker-compose logs
	docker-compose logs -f

# ── Trivy Security Scan ──────────────────────────────────────
trivy: build ## Scan Docker image for vulnerabilities with Trivy
	trivy image --severity CRITICAL,HIGH $(IMAGE_NAME):$(IMAGE_TAG)

# ── Cleanup ──────────────────────────────────────────────────
clean: ## Remove Python artifacts and coverage files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .coverage htmlcov/ coverage.xml dist/ build/
