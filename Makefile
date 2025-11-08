.PHONY: help install install-dev test lint format type-check clean docs serve-docs
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Toyota GR Cup Analytics - Development Commands"
	@echo "=============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv sync

install-dev: ## Install with development dependencies
	uv sync --dev

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src/toyota_gr_cup_analytics --cov-report=html --cov-report=term

lint: ## Run linting
	uv run flake8 src/ tests/
	uv run isort --check-only --diff src/ tests/
	uv run black --check src/ tests/

format: ## Format code
	uv run isort src/ tests/
	uv run black src/ tests/

type-check: ## Run type checking
	uv run mypy src/

clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs: ## Build documentation
	cd docs && uv run sphinx-build -b html . _build/html

serve-docs: docs ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8000

run-dashboard: ## Run the interactive dashboard
	uv run gr-analytics dashboard --debug

analyze-barber: ## Quick analysis of Barber track
	uv run gr-analytics analyze --track barber --race 1

setup-pre-commit: ## Set up pre-commit hooks
	uv run pre-commit install

check-all: lint type-check test ## Run all checks