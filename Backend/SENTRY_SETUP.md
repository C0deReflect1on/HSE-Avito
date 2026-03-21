# Sentry Setup Guide

## Overview

This guide explains how to set up and configure Sentry for error tracking in the moderation service.

## Self-hosted Sentry with Docker

The `docker-compose.yaml` includes a self-hosted Sentry installation with the following services:

- `sentry`: Main Sentry web application (port 9000)
- `sentry-worker`: Background worker for processing events
- `sentry-cron`: Scheduled tasks runner
- `sentry-postgres`: PostgreSQL database for Sentry
- `sentry-redis`: Redis cache for Sentry

### Starting Sentry

```bash
cd HSE-Avito/Backend
docker-compose up -d sentry-postgres sentry-redis
docker-compose run --rm sentry upgrade
docker-compose up -d sentry sentry-worker sentry-cron
```

The `sentry upgrade` command will:
- Initialize the database schema
- Create a default admin user (you'll be prompted for email/password)
- Set up the default organization

### Accessing Sentry

1. Open http://localhost:9000 in your browser
2. Log in with the credentials you created during setup
3. Create a new project:
   - Select "Python" as the platform
   - Name it "moderation-api"
   - Copy the DSN (Data Source Name)

### Configuring the Application

Add the DSN to your environment variables:

```bash
export SENTRY_DSN="http://your-sentry-dsn@localhost:9000/1"
export SENTRY_ENVIRONMENT="development"
export SENTRY_TRACES_SAMPLE_RATE="1.0"
```

Or update the `docker-compose.yaml` file:

```yaml
api:
  environment:
    SENTRY_DSN: "http://your-sentry-dsn@localhost:9000/1"
    SENTRY_ENVIRONMENT: "development"
    SENTRY_TRACES_SAMPLE_RATE: "1.0"
```

## Testing Sentry Integration

### Triggering Test Errors

1. **Model Unavailable Error**:
```bash
curl -X POST http://localhost:8003/predict \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": 1,
    "item_id": 999999,
    "is_verified_seller": false,
    "name": "Test",
    "description": "Test",
    "category": 1,
    "images_qty": 1
  }'
```

2. **Model Prediction Error**: Stop the model or corrupt model file, then make a prediction request.

3. **Database Error**: Make a request with invalid data that triggers a database constraint violation.

### Viewing Errors in Sentry

1. Go to http://localhost:9000
2. Navigate to "Issues"
3. You should see captured exceptions with:
   - Stack traces
   - Request context (URL, headers, body)
   - Environment info (Python version, dependencies)
   - Breadcrumbs (sequence of events leading to error)

## Error Handling

The application captures the following exceptions in Sentry:

- `ModerationError`: General moderation errors (422 status)
- `ModelPredictionError`: Model prediction failures (500 status)
- `ModelUnavailableError`: Model not available (503 status)
- `asyncpg.exceptions.UndefinedTableError`: Database schema issues (503 status)

All captured errors include:
- Full stack trace
- Request URL and method
- Request headers and body
- User context (if authenticated)
- Server environment

## Configuration

### Settings

Configuration is managed through environment variables in `app/settings.py`:

```python
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "development")
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
```

### Integrations

The application uses:

- `FastApiIntegration`: Automatic FastAPI request/response tracking
- `AsyncPGIntegration`: Database query tracking and error capture

## Production Considerations

For production deployment:

1. Use a managed Sentry service (sentry.io) or properly configured self-hosted instance
2. Reduce `SENTRY_TRACES_SAMPLE_RATE` to avoid performance impact (e.g., 0.1 for 10% sampling)
3. Configure alert rules for critical errors
4. Set up proper user context with authentication info
5. Use environment tags to differentiate staging/production errors

## Alternative: Using sentry.io

Instead of self-hosted Sentry, you can use the free sentry.io tier:

1. Sign up at https://sentry.io
2. Create a new project
3. Copy the DSN
4. Set `SENTRY_DSN` environment variable
5. No Docker services needed for Sentry
