.PHONY: help install lint format test runserver migrate seed shell check e2e clean

PYTHON := python
PIP := pip
DJANGO := $(PYTHON) manage.py

PORT := 8000

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies (dev = prod + tooling)
	$(PIP) install -r requirements-dev.txt
	playwright install chromium

pre-commit: ## Install pre-commit hooks
	$(PYTHON) -m pre_commit install

lint: ## Run ruff linter
	$(PYTHON) -m ruff check .

format: ## Run ruff formatter
	$(PYTHON) -m ruff format .

format-check: ## Check formatting without changes
	$(PYTHON) -m ruff format --check .

check: lint format-check ## Lint + format check (CI)

test: ## Run pytest (unit tests only)
	SECRET_KEY=test DEBUG=True $(PYTHON) -m pytest -q --tb=short

test-cov: ## Run pytest with coverage
	SECRET_KEY=test DEBUG=True $(PYTHON) -m pytest --cov --cov-report=term

e2e: ## Run Playwright E2E tests (requires Python 3.13)
	SECRET_KEY=test DEBUG=True $(PYTHON) -m pytest e2e/ -m e2e -v

migrate: ## Run Django migrations
	$(DJANGO) migrate

seed: ## Create test users
	$(DJANGO) seed_test_users

shell: ## Open Django shell
	$(DJANGO) shell

runserver: ## Start development server
	SECRET_KEY=test-key-not-for-production DEBUG=True $(DJANGO) runserver $(PORT)

collectstatic: ## Collect static files
	$(DJANGO) collectstatic --noinput --clear

start: migrate collectstatic runserver ## Full dev setup: migrate + static + server

clean: ## Remove Python cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf staticfiles/ 2>/dev/null || true

setup: install pre-commit migrate seed collectstatic runserver ## Full project setup for new devs
