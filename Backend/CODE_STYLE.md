# Backend Code Style Guide

This document describes the coding conventions and patterns used in the HSE-Avito Backend project. Follow these guidelines when adding new features or modifying existing code.

## General Principles

### Python Version
- Python 3.11+
- Use modern Python features: type hints, dataclasses, union types with `|` operator

### Code Organization
- Keep modules focused on single responsibility
- Use Protocol classes for interfaces
- Prefer composition over inheritance
- Use dataclasses for data structures
- Use frozen dataclasses for immutable services

## Import Conventions

### Order
1. Standard library imports
2. Third-party library imports
3. Local application imports

### Style
```python
import asyncio
import json
import logging
from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, Depends
from redis.asyncio import Redis

from app.repositories.moderation_repository import ModerationRepository
from app.schemas import PredictRequest, PredictResponse
from app.settings import KAFKA_BOOTSTRAP, MODERATION_TOPIC
```

### Rules
- Use absolute imports from `app.` prefix
- Group imports by category (separated by blank lines)
- Sort imports alphabetically within groups
- Import specific items rather than modules when possible

## Type Annotations

### Required
- All function parameters must have type annotations
- All function return types must be specified
- Use `None` instead of omitting return type

### Patterns
```python
# Function signatures
def process_data(item_id: int, payload: dict[str, Any]) -> bool:
    pass

async def fetch_item(item_id: int) -> dict[str, Any] | None:
    pass

# Union types with modern syntax
def get_result() -> PredictResponse | None:
    pass

# Protocol definitions
class ModelProvider(Protocol):
    def predict_proba(self, features: list[float]) -> float: ...
```

### Avoid
- Do not use old-style `Union[A, B]` syntax (use `A | B`)
- Do not use `Optional[T]` (use `T | None`)

## Dataclasses and Services

### Service Layer Pattern
```python
@dataclass(frozen=True)
class ModerationService:
    _repository: ModerationRepository
    _availability_checker: ServiceAvailability
    _model_provider: ModelProvider
    
    def predict(self, payload: PredictRequest) -> PredictResponse:
        # Implementation
        pass
```

### Rules
- Use `frozen=True` for service classes (immutable)
- Prefix private fields with underscore
- Inject dependencies through constructor
- No mutable state in services

### Repository Pattern
```python
@dataclass(frozen=True)
class ModerationRepository:
    _storage: InMemoryStorage
    _cache_ref: _CacheRef = field(default_factory=_CacheRef)
    
    async def get_by_id(self, task_id: int) -> dict[str, Any] | None:
        pass
```

## Async/Await Conventions

### When to Use
- All I/O operations (database, Redis, Kafka)
- HTTP request handlers
- Worker message processing

### Patterns
```python
# Async function
async def fetch_data(item_id: int) -> dict[str, Any] | None:
    pool = get_pool()
    async with track_db_select():
        row = await pool.fetchrow("SELECT * FROM items WHERE id = $1", item_id)
        return dict(row) if row is not None else None
```

### Rules
- Use `async def` for async functions
- Use `await` for async calls
- Use async context managers (`async with`)
- Return `None` explicitly for nullable results

## Error Handling

### Custom Exceptions
```python
class ModerationError(Exception):
    pass

class ModelUnavailableError(ModerationError):
    pass

class ModelPredictionError(ModerationError):
    pass
```

### Patterns
```python
# Raise custom exceptions with context
if self._model is None:
    raise ModelUnavailableError("moderation model is not loaded")

# Catch and re-raise with context
try:
    probability = self._model.predict_proba(features)
except Exception as exc:
    raise ModelPredictionError("predictions are unavailable") from exc
```

### HTTP Exceptions in Routers
```python
@router.post("/predict")
async def predict(payload: PredictRequest) -> PredictResponse:
    if not data:
        raise HTTPException(status_code=404, detail="item not found")
    return result
```

## Logging

### Setup
```python
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
```

### Patterns
```python
# Info logging with parameters
logger.info(
    "Prediction request seller_id=%s item_id=%s features=%s",
    payload.seller_id,
    payload.item_id,
    normalized_features,
)

# Exception logging
logger.exception("Moderation failed: %s", e)

# Worker logging
logger.info("Worker started. Consuming topic=%s group=%s", MODERATION_TOPIC, CONSUMER_GROUP)
```

### Rules
- Use structured logging with parameters (not f-strings in log messages)
- Use `logger.exception()` in except blocks
- Log at appropriate levels (INFO for normal flow, ERROR for failures)

## FastAPI Patterns

### Router Setup
```python
router = APIRouter()

# Module-level service instances
availability_checker = AlwaysAvailableService()
model_provider = ModerationModelProvider()
moderation_service = ModerationService(repository, availability_checker, model_provider)
```

### Endpoint Patterns
```python
@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    account: Account = Depends(get_current_account),
) -> PredictResponse:
    _ = account  # Acknowledge unused but required dependency
    return moderation_service.predict(payload)

@router.post("/async_predict")
async def async_predict(
    payload: SimplePredictRequest,
    producer: KafkaProducer = Depends(get_kafka_producer),
    account: Account = Depends(get_current_account),
) -> AsyncPredictResponse:
    # Implementation
    pass
```

### Rules
- Use explicit `response_model` when applicable
- Use `Depends()` for dependency injection
- Use `_ = variable` to acknowledge intentionally unused dependencies
- Separate sync and async handlers appropriately

## Database Access

### Using Context Managers
```python
async def get_by_id(self, task_id: int) -> dict[str, Any] | None:
    pool = get_pool()
    async with track_db_select():
        row = await pool.fetchrow(
            """
            SELECT id, item_id, status
            FROM moderation_results
            WHERE id = $1
            """,
            task_id,
        )
        return dict(row) if row is not None else None
```

### SQL Formatting
```python
# Multi-line SQL with proper indentation
row = await pool.fetchrow(
    """
    SELECT
        id,
        item_id,
        status,
        is_violation,
        probability
    FROM moderation_results
    WHERE id = $1
    """,
    task_id,
)

# Single-line for simple queries
await pool.execute("DELETE FROM items WHERE id = $1", item_id)
```

### Rules
- Use parameterized queries (never string interpolation)
- Wrap DB calls with metric tracking context managers
- Use triple-quoted strings for multi-line SQL
- Return `dict(row)` for row results, `None` for not found

## Cache Key Conventions

### Pattern
```python
# Format: entity_type:identifier_type:identifier_value
cache_key = f"item_prediction:item_id:{item_id}"
cache_key = f"moderation_task:{task_id}"
```

### Rules
- Use descriptive prefixes
- Use colons as separators
- Include entity type and identifier

## Worker Patterns

### Main Function Structure
```python
async def main() -> None:
    await db.connect()
    
    # Initialize components
    model_provider = ModerationModelProvider()
    model_provider.load()
    
    # Setup consumers/producers
    consumer = AIOKafkaConsumer(...)
    dlq = AIOKafkaProducer(...)
    
    await consumer.start()
    await dlq.start()
    
    logger.info("Worker started. Consuming topic=%s", TOPIC)
    
    try:
        async for msg in consumer:
            # Process message
            pass
    finally:
        await consumer.stop()
        await dlq.stop()
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Message Processing
```python
async for msg in consumer:
    task_id = None
    item_id = None
    event = {}
    try:
        event = json.loads(msg.value.decode("utf-8"))
        task_id = int(event["task_id"])
        item_id = int(event["item_id"])
        
        # Process message
        
        await consumer.commit()
    except Exception as e:
        logger.exception("Processing failed: %s", e)
        # Send to DLQ
        await consumer.commit()
```

## Testing Conventions

### Test Markers
```python
import pytest

pytestmark = pytest.mark.unit  # or pytest.mark.integration

@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Fixture Patterns
```python
@pytest.fixture
def payload_factory():
    def _factory(**overrides):
        payload = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 10,
        }
        payload.update(overrides)
        return payload
    return _factory
```

### Mock Patterns
```python
# Patching with context managers
with patch.object(provider, "predict_proba", return_value=0.8):
    response = client.post("/predict", json=payload)

# AsyncMock for async functions
with patch("module.function", new=AsyncMock(return_value=result)):
    await function_call()
```

## Configuration and Settings

### Pattern
```python
import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
API_PORT = int(os.getenv("API_PORT", "8000"))
USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"
```

### Rules
- Load environment variables at module level
- Provide sensible defaults
- Convert types explicitly (int, bool)
- Use `.lower() == "true"` for boolean flags

## Naming Conventions

### Variables and Functions
- `snake_case` for variables, functions, methods
- `_private_method` for private/internal methods
- `UPPER_CASE` for constants

### Classes
- `PascalCase` for class names
- Descriptive names: `ModerationService`, `AccountRepository`

### Modules
- `snake_case` for module/package names
- Descriptive: `model_provider.py`, `moderation_repository.py`

## Documentation

### Docstrings
```python
def load_model_from_mlflow(model_name: str) -> Any:
    """Load model from MLflow Model Registry.
    
    Args:
        model_name: Name of the registered model
        
    Returns:
        Loaded model instance
        
    Raises:
        ModelUnavailableError: If model cannot be loaded
    """
    pass
```

### Comments
```python
# Good: Explain why, not what
# Cache hit - skip model inference and use cached result
if cached_result is not None:
    return cached_result

# Bad: Obvious comments
# Get the user ID
user_id = payload.user_id
```

### Rules
- Write docstrings for public functions and classes
- Use comments to explain non-obvious logic
- Avoid obvious comments that repeat the code
- Keep comments up-to-date with code changes

## Code Quality

### Avoid
- Global mutable state
- Hardcoded strings (use constants)
- Nested if statements (use early returns)
- Large functions (split into smaller functions)
- Magic numbers (use named constants)

### Prefer
- Immutable data structures
- Early returns for validation
- Small, focused functions
- Dependency injection
- Type hints everywhere
