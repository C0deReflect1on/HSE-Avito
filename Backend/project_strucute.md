# Backend Project Structure

This file describes the main directories and files in the `Backend/` project and their purpose.

## Root

- `app/` - Main application code (API, business logic, data access, workers).
- `db/` - Database migration scripts and migration runner config.
- `grafana/` - Grafana dashboard and provisioning configuration.
- `scripts/` - Utility scripts for setup and operations (MLflow model registration).
- `tests/` - Automated tests (unit, integration, async, cache).
- `Dockerfile` - Container image build instructions for the backend service.
- `docker-compose.yaml` - Local/dev stack orchestration (app + infra services).
- `main.py` - Entry point script for launching the application.
- `requirements.txt` - Python dependencies (includes `pyjwt` for JWT auth, `mlflow` for model management).
- `pytest.ini` - Pytest configuration (markers: `unit`, `integration`).
- `prometheus.yml` - Prometheus scrape/configuration file.
- `load_test.py` - Python load testing script.
- `load_test.sh` - Shell script for running load tests.
- `auth_smoke_test.sh` - Shell script for manual auth smoke testing via curl.
- `MONITORING.md` - Monitoring/observability setup and usage documentation.
- `CODE_STYLE.md` - Code style guide and conventions for the project.

## `app/`

- `main.py` - FastAPI app initialization, routers registration, startup wiring.
- `settings.py` - Centralized runtime configuration and environment settings.
- `config.py` - JWT configuration (secret, algorithm, expiration).
- `deps.py` - Dependency providers for request handlers (Kafka).
- `dependencies.py` - Auth dependency (`get_current_account`) for protected endpoints.
- `schemas.py` - API/data schemas (request/response models, `Account`, `LoginRequest`).
- `exceptions.py` - Custom exception classes (`AuthenticationError`, `AccountBlockedError`, `InvalidTokenError`).
- `metrics.py` - Prometheus metrics declarations and helpers.
- `db.py` - Database connection/session helpers.
- `model.py` - Model-related domain structures or shared model definitions.

### `app/clients/`

- `kafka.py` - Kafka producer/consumer client setup and helpers.

### `app/repositories/`

- `items.py` - Data access for items domain entities.
- `users.py` - Data access for users domain entities.
- `moderation_repository.py` - Data access for moderation entities/results.
- `account_repository.py` - Data access for account entities (CRUD, block, credentials lookup).
- `__init__.py` - Package marker/exports (`AccountRepository`).

### `app/routers/`

- `auth.py` - `POST /login` endpoint (JWT authentication, HttpOnly cookie).
- `predict.py` - API endpoints for prediction/moderation requests (auth-protected).
- `moderation_result.py` - API endpoints for fetching moderation outcomes (auth-protected).
- `__init__.py` - Package marker/router module exports.

### `app/services/`

- `moderation.py` - Core moderation business logic/orchestration.
- `model_provider.py` - ML model/provider loading and inference adapter (supports local and MLflow modes).
- `auth_service.py` - JWT auth service (authenticate, create/verify token).
- `password_hasher.py` - Password hashing utility (md5).
- `__init__.py` - Package marker for service exports.

### `app/storage/`

- `redis_cache.py` - Redis-backed cache implementation.
- `memory.py` - In-memory fallback/local cache implementation.
- `__init__.py` - Shared storage interfaces or exports.

### `app/utils/`

- `metrics.py` - Async context managers for database query metrics tracking.
- `__init__.py` - Package marker for utility exports.

### `app/workers/`

- `moderation_worker.py` - Background moderation processing worker.
- `dlq_worker.py` - Dead-letter queue worker for failed message handling.

## `scripts/`

- `register_model_mlflow.py` - Script to train and register moderation model in MLflow Model Registry.

## `db/`

- `migrate.sh` - Script to run database migrations.
- `migrations.yml` - Migration tool configuration.
- `migrations/` - SQL migration files:
  - `V001__initial.sql` - Initial schema setup.
  - `V002__moderation_results.sql` - Moderation results schema changes.
  - `V003__items_is_closed.sql` - Items table/status-related schema update.
  - `V004__account.sql` - Account table for JWT auth (login, hashed password, is_blocked).

## `grafana/`

- `dashboards/moderation_dashboard.json` - Predefined moderation dashboard.
- `provisioning/dashboards/default.yml` - Dashboard auto-provisioning config.
- `provisioning/datasources/prometheus.yml` - Prometheus datasource config.

## `tests/`

- `conftest.py` - Shared fixtures and test setup (auth override for existing tests).
- `test_predict.py` - Prediction endpoint behavior tests (unit).
- `test_prediction_cache.py` - Caching behavior tests for predictions.
- `test_async_moderation.py` - Async moderation flow tests (integration).
- `test_repositories.py` - Repository-level data access tests (integration).
- `test_postgres_integration.py` - Postgres integration tests.
- `test_moderation_result_unit.py` - Unit tests for moderation result logic.
- `test_account_repository.py` - Account repository integration tests (CRUD, block, delete).
- `test_auth_service_unit.py` - Unit tests for AuthService (authenticate, token create/verify).
- `test_auth_router.py` - Integration tests for POST /login (200/401/403/422, cookie).
- `test_auth_dependency_unit.py` - Unit tests for get_current_account dependency (token/cookie checks).

## Notes

- Generated/cached development files (for example, `.pytest_cache/`) are intentionally not described as part of business logic.
