.PHONY: help install dev-install test lint format clean build docker-build docker-run setup completions

PROJECT := pxrun
SRC_DIR := src
TEST_DIR := tests

# Default target
help:
	@echo "Available targets:"
	@echo "  setup         - Install uv and create virtual environment"
	@echo "  install       - Install the package in production mode"
	@echo "  dev-install   - Install the package in development mode with all dependencies"
	@echo "  test          - Run all tests with coverage"
	@echo "  test-contract - Run contract tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint          - Run linters (ruff, mypy)"
	@echo "  format        - Format code with black and ruff"
	@echo "  clean         - Remove build artifacts and cache files"
	@echo "  build         - Build distribution packages"
	@echo "  completions   - Generate shell completions"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"

# Setup and installation targets
setup:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv venv
	@echo "Run 'source .venv/bin/activate' to activate the virtual environment"
	@echo "Then run 'make dev-install' to install development dependencies"

install:
	uv pip install .

dev-install:
	uv pip install -e ".[dev]"
	pre-commit install

# Testing targets
test:
	pytest $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-contract:
	pytest $(TEST_DIR)/contract -v

test-integration:
	pytest $(TEST_DIR)/integration -v -m "not slow"

# Code quality targets
lint:
	ruff check $(SRC_DIR) $(TEST_DIR)
	mypy $(SRC_DIR)

format:
	black $(SRC_DIR) $(TEST_DIR)
	ruff check --fix $(SRC_DIR) $(TEST_DIR)

check: lint
	black --check $(SRC_DIR) $(TEST_DIR)

# Build targets
build: clean
	uv build
	uvx twine check dist/*

# Generate shell completions
completions:
	python3 -m src.utils.completions

# Clean targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Docker targets
docker-build:
	docker build -t $(PROJECT):latest .

docker-run:
	docker run --rm -it \
		-v ~/.ssh:/home/pxrun/.ssh:ro \
		--env-file .env \
		$(PROJECT):latest

# Development workflow
dev: setup dev-install
	@echo "Development environment ready!"
	@echo "Activate with: source .venv/bin/activate"

ci: lint test
	@echo "CI checks passed!"

# Release targets
publish-test: build
	uvx twine upload --repository-url https://test.pypi.org/legacy/ dist/*
	@echo "Test with: uv pip install --index-url https://test.pypi.org/simple/ pxrun"

publish: build
	uvx twine upload dist/*