.PHONY: help test start stop logs clean restart

help:
	@echo "========================================="
	@echo "Papelería Boyacá - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Service Management:"
	@echo "  make start              Start all services with docker-compose"
	@echo "  make stop               Stop all running services"
	@echo "  make restart            Restart all services"
	@echo "  make logs               Show docker-compose logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test               Run all tests"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-integration   Run integration tests"
	@echo "  make test-cov           Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make lint               Run code linting (flake8)"
	@echo "  make format             Format code with black and isort"
	@echo "  make type-check         Run type checking with mypy"
	@echo "  make clean              Remove __pycache__ and .pytest_cache"
	@echo ""
	@echo "Database:"
	@echo "  make db-reset           Reset database (WARNING: deletes all data)"
	@echo "  make db-migrations      Run Alembic migrations"
	@echo ""

test: test-unit

test-unit:
	@echo "=== Tests unitarios (SQLite en memoria — sin contenedores) ==="
	@cd identity-service && pytest tests/ -v -m "not integration" -p no:warnings && cd ..
	@cd catalog-service  && pytest tests/ -v -m "not integration" -p no:warnings && cd ..
	@cd order-service    && pytest tests/ -v -m "not integration" -p no:warnings && cd ..
	@cd payment-service  && pytest tests/ -v -m "not integration" -p no:warnings && cd ..
	@cd api-gateway      && pytest tests/ -v -m "not integration" -p no:warnings && cd ..

test-db-up:
	@echo "=== Levantando BD de tests (puerto 5433) ==="
	@docker compose -f deploy/docker-compose.test.yml up -d --wait

test-db-down:
	@docker compose -f deploy/docker-compose.test.yml down -v

test-integration: test-db-up
	@echo "=== Tests de integración contra PostgreSQL ==="
	@TEST_DATABASE_URL="postgresql+asyncpg://postgres:testpass@localhost:5433/papeleria_test" \
		pytest tests_integration/ -v -m integration -p no:warnings
	@$(MAKE) test-db-down

test-cov:
	@echo "=== Cobertura (tests unitarios) ==="
	@cd identity-service && pytest tests/ -m "not integration" --cov=src --cov-report=term-missing && cd ..
	@cd catalog-service  && pytest tests/ -m "not integration" --cov=src --cov-report=term-missing && cd ..
	@cd order-service    && pytest tests/ -m "not integration" --cov=src --cov-report=term-missing && cd ..
	@cd payment-service  && pytest tests/ -m "not integration" --cov=src --cov-report=term-missing && cd ..
	@cd api-gateway      && pytest tests/ -m "not integration" --cov=src --cov-report=term-missing && cd ..

lint:
	@echo "Running flake8 linter..."
	@flake8 identity-service/src catalog-service/src order-service/src payment-service/src --max-line-length=120

format:
	@echo "Formatting code with black..."
	@black identity-service/src catalog-service/src order-service/src payment-service/src
	@echo "Sorting imports with isort..."
	@isort identity-service/src catalog-service/src order-service/src payment-service/src

type-check:
	@echo "Running mypy type checking..."
	@mypy identity-service/src --ignore-missing-imports
	@mypy catalog-service/src --ignore-missing-imports
	@mypy order-service/src --ignore-missing-imports
	@mypy payment-service/src --ignore-missing-imports

clean:
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleanup completed"

start:
	@docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build --no-cache

stop:
	@docker compose -f deploy/docker-compose.yml --env-file deploy/.env down

restart: stop start

logs:
	@docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs -f

db-reset:
	@echo "WARNING: This will delete all data from the database!"
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd deploy && docker-compose --env-file deploy/.env down -v; \
		bash start_services.sh; \
	fi

db-migrations:
	@echo "Running database migrations..."
	@alembic upgrade head
