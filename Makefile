.PHONY: help install dev-install test lint format clean build docker-build docker-run

PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT := pxrun
SRC_DIR := src
TEST_DIR := tests

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install the package in production mode"
	@echo "  dev-install   - Install the package in development mode with all dependencies"
	@echo "  test          - Run all tests with coverage"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint          - Run linters (ruff, mypy)"
	@echo "  format        - Format code with black"
	@echo "  clean         - Remove build artifacts and cache files"
	@echo "  build         - Build distribution packages"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"

# Installation targets
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install .

dev-install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	pre-commit install

# Testing targets
test:
	pytest $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-unit:
	pytest $(TEST_DIR)/unit -v

test-integration:
	pytest $(TEST_DIR)/integration -v -m "not slow"

test-contract:
	pytest $(TEST_DIR)/contract -v

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
	$(PYTHON) -m build
	twine check dist/*

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
dev: dev-install
	@echo "Development environment ready!"

ci: lint test
	@echo "CI checks passed!"

# Release targets
release-test: build
	twine upload --repository testpypi dist/*

release: build
	twine upload dist/*