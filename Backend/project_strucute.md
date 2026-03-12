# Backend Project Structure

This file describes the main directories and files in the `Backend/` project and their purpose.

## Root

- `app/` - Main application code (API, business logic, data access, workers).
- `db/` - Database migration scripts and migration runner config.
- `grafana/` - Grafana dashboard and provisioning configuration.
- `tests/` - Automated tests (unit, integration, async, cache).
- `Dockerfile` - Container image build instructions for the backend service.
- `docker-compose.yaml` - Local/dev stack orchestration (app + infra services).
- `main.py` - Entry point script for launching the application.
- `requirements.txt` - Python dependencies.
- `pytest.ini` - Pytest configuration.
- `prometheus.yml` - Prometheus scrape/configuration file.
- `load_test.py` - Python load testing script.
- `load_test.sh` - Shell script for running load tests.
- `MONITORING.md` - Monitoring/observability setup and usage documentation.

## `app/`

- `main.py` - FastAPI app initialization, routers registration, startup wiring.
- `settings.py` - Centralized runtime configuration and environment settings.
- `deps.py` - Dependency providers for request handlers.
- `schemas.py` - API/data schemas (request/response models).
- `exceptions.py` - Custom exception classes and error abstractions.
- `metrics.py` - Prometheus metrics declarations and helpers.
- `db.py` - Database connection/session helpers.
- `model.py` - Model-related domain structures or shared model definitions.

### `app/clients/`

- `kafka.py` - Kafka producer/consumer client setup and helpers.

### `app/repositories/`

- `items.py` - Data access for items domain entities.
- `users.py` - Data access for users domain entities.
- `moderation_repository.py` - Data access for moderation entities/results.
- `__init__.py` - Package marker for repository module exports.

### `app/routers/`

- `predict.py` - API endpoints for prediction/moderation requests.
- `moderation_result.py` - API endpoints for fetching moderation outcomes.
- `__init__.py` - Package marker/router module exports.

### `app/services/`

- `moderation.py` - Core moderation business logic/orchestration.
- `model_provider.py` - ML model/provider loading and inference adapter.
- `__init__.py` - Package marker for service exports.

### `app/storage/`

- `redis_cache.py` - Redis-backed cache implementation.
- `memory.py` - In-memory fallback/local cache implementation.
- `__init__.py` - Shared storage interfaces or exports.

### `app/workers/`

- `moderation_worker.py` - Background moderation processing worker.
- `dlq_worker.py` - Dead-letter queue worker for failed message handling.

## `db/`

- `migrate.sh` - Script to run database migrations.
- `migrations.yml` - Migration tool configuration.
- `migrations/` - SQL migration files:
  - `V001__initial.sql` - Initial schema setup.
  - `V002__moderation_results.sql` - Moderation results schema changes.
  - `V003__items_is_closed.sql` - Items table/status-related schema update.

## `grafana/`

- `dashboards/moderation_dashboard.json` - Predefined moderation dashboard.
- `provisioning/dashboards/default.yml` - Dashboard auto-provisioning config.
- `provisioning/datasources/prometheus.yml` - Prometheus datasource config.

## `tests/`

- `conftest.py` - Shared fixtures and test setup.
- `test_predict.py` - Prediction endpoint behavior tests.
- `test_prediction_cache.py` - Caching behavior tests for predictions.
- `test_async_moderation.py` - Async moderation flow tests.
- `test_repositories.py` - Repository-level data access tests.
- `test_postgres_integration.py` - Postgres integration tests.
- `test_moderation_result_unit.py` - Unit tests for moderation result logic.

## Notes

- Generated/cached development files (for example, `.pytest_cache/`) are intentionally not described as part of business logic.
