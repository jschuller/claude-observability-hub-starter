# Claude Observability Hub - Makefile
# Convenience commands for development and testing

.PHONY: help test test-all test-python test-bun test-vue test-integration \
        coverage lint format docker-up docker-down docker-test clean install \
        devcontainer-build devcontainer-up devcontainer-test multi-machine

# Default target
help:
	@echo "Claude Observability Hub - Available Commands:"
	@echo "=============================================="
	@echo "  make install          Install all dependencies"
	@echo "  make test-all         Run all tests"
	@echo "  make test-python      Run Python tests"
	@echo "  make test-bun         Run Bun/TypeScript tests"
	@echo "  make test-vue         Run Vue tests"
	@echo "  make test-integration Run integration tests"
	@echo "  make coverage         Generate coverage reports"
	@echo "  make lint             Run all linters"
	@echo "  make format           Format all code"
	@echo "  make docker-up        Start services"
	@echo "  make docker-down      Stop services"
	@echo "  make docker-test      Run tests in Docker"
	@echo "  make devcontainer-build Build DevContainer"
	@echo "  make devcontainer-up  Start DevContainer"
	@echo "  make devcontainer-test Test in DevContainer"
	@echo "  make multi-machine    Run multi-machine simulation"
	@echo "  make clean            Clean build artifacts"

# Install dependencies
install:
	pip install -r requirements-dev.txt
	cd core/server && bun install
	cd core/dashboard && npm install

# Run all tests
test-all:
	./scripts/test-all.sh

# Individual test targets
test-python:
	./scripts/test-python.sh

test-bun:
	cd core/server && bun test

test-vue:
	cd core/dashboard && npm test

test-integration:
	docker-compose -f docker-compose.test.yml up -d test-hub
	sleep 5
	pytest tests/integration/ -v
	docker-compose -f docker-compose.test.yml down -v

# Coverage reports
coverage:
	@echo "Generating coverage reports..."
	pytest --cov --cov-report=html
	cd core/server && bun test --coverage
	cd core/dashboard && npm run test:coverage
	python scripts/test-summary.py

# Linting
lint:
	black --check templates/
	ruff check templates/
	cd core/server && bun run lint
	cd core/dashboard && npm run lint

# Code formatting
format:
	black templates/
	ruff check --fix templates/
	cd core/server && bun run format
	cd core/dashboard && npm run format

# Docker operations
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-test:
	docker-compose -f docker-compose.test.yml run --rm python-tests
	docker-compose -f docker-compose.test.yml run --rm node-tests
	docker-compose -f docker-compose.test.yml run --rm vue-tests

# DevContainer operations
devcontainer-build:
	devcontainer build --workspace-folder .

devcontainer-up:
	devcontainer up --workspace-folder .

devcontainer-test:
	devcontainer exec --workspace-folder . bash scripts/test-all-devcontainer.sh

# Multi-machine simulation
multi-machine:
	./scripts/test-multi-machine.sh

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "coverage" -exec rm -rf {} +
	find . -type d -name "test-results" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete