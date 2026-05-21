.PHONY: help install dev test lint format build up down logs migrate seed clean docker-build docker-push

.DEFAULT_GOAL := help

PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := synthetic-bank-data
DOCKER_REGISTRY := ghcr.io
DOCKER_IMAGE := $(DOCKER_REGISTRY)/$(PROJECT_NAME)

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Display this help message
	@echo "$(BLUE)SyntheticBankData - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install project dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

dev: ## Run development server with hot reload
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests with coverage
	$(PYTHON) -m pytest --cov=app --cov-report=html --cov-report=term-missing -v

test-fast: ## Run tests without coverage
	$(PYTHON) -m pytest -v

test-watch: ## Run tests in watch mode
	$(PYTHON) -m pytest-watch -- -v

lint: ## Run ruff linter
	$(PYTHON) -m ruff check .

format: ## Format code with ruff
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check . --fix

type-check: ## Run mypy type checker
	$(PYTHON) -m mypy app/ --strict --ignore-missing-imports

build: ## Build Python package
	$(PYTHON) setup.py build

clean: ## Remove build artifacts, cache, and temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.coverage' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info .tox/
	@echo "$(GREEN)✓ Cleaned build artifacts$(NC)"

up: ## Start Docker containers
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Containers started$(NC)"
	@echo "API available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

down: ## Stop Docker containers
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

logs: ## Show Docker container logs
	$(DOCKER_COMPOSE) logs -f

logs-app: ## Show application logs only
	$(DOCKER_COMPOSE) logs -f app

logs-db: ## Show database logs only
	$(DOCKER_COMPOSE) logs -f db

migrate: ## Run database migrations
	$(DOCKER_COMPOSE) exec app alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

migrate-down: ## Rollback last migration
	$(DOCKER_COMPOSE) exec app alembic downgrade -1
	@echo "$(GREEN)✓ Rollback completed$(NC)"

migrate-create: ## Create new migration (usage: make migrate-create MSG="migration message")
	$(DOCKER_COMPOSE) exec app alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database with sample data
	@bash scripts/seed.sh
	@echo "$(GREEN)✓ Database seeded$(NC)"

backup: ## Backup database
	@bash scripts/backup.sh
	@echo "$(GREEN)✓ Backup completed$(NC)"

docker-build: ## Build Docker image locally
	docker build -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-push: ## Push Docker image to registry
	docker tag $(PROJECT_NAME):latest $(DOCKER_IMAGE):latest
	docker push $(DOCKER_IMAGE):latest
	@echo "$(GREEN)✓ Docker image pushed$(NC)"

shell: ## Open Python shell with app context
	$(PYTHON) -m IPython

db-shell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec db psql -U postgres -d synthetic_bank

restart: ## Restart all containers
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Containers restarted$(NC)"

status: ## Show container status
	$(DOCKER_COMPOSE) ps

requirements: ## Generate requirements from pipdeptree
	$(PIP) install pipdeptree
	pipdeptree > requirements-tree.txt
	@echo "$(GREEN)✓ Requirements tree generated$(NC)"

freeze: ## Freeze current dependencies
	$(PIP) freeze > requirements-frozen.txt
	@echo "$(GREEN)✓ Requirements frozen$(NC)"

security: ## Run security checks
	$(PYTHON) -m safety check
	$(PYTHON) -m bandit -r app/ -ll
	@echo "$(GREEN)✓ Security checks completed$(NC)"

docs: ## Generate API documentation
	$(PYTHON) -m mkdocs build
	@echo "$(GREEN)✓ Documentation generated in site/$(NC)"

docs-serve: ## Serve documentation locally
	$(PYTHON) -m mkdocs serve

.PHONY: help install dev test lint format build up down logs migrate seed clean docker-build docker-push
