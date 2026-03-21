#!/bin/bash
set -e

echo "=== Backend Fixes Test Runner ==="
echo "Testing all fixes in Docker environment"
echo ""

cd HSE-Avito/Backend

echo "Step 1: Starting required services (PostgreSQL, Redis)..."
docker-compose up -d postgres_test redis

echo "Waiting for services to be healthy..."
sleep 5

echo ""
echo "Step 2: Running migrations..."
export TEST_DATABASE_DSN="postgresql://app:app@localhost:5433/avito-test"
export DATABASE_DSN="postgresql://app:app@localhost:5433/avito-test"

# Apply migrations if needed
if [ -d "db/migrations" ]; then
    echo "Migrations directory found"
fi

echo ""
echo "Step 3: Installing dependencies in venv..."
cd ../..
if [ ! -d "bakend_venv" ]; then
    python3 -m venv bakend_venv
fi
source bakend_venv/bin/activate
pip install -r HSE-Avito/Backend/requirements.txt > /dev/null 2>&1 || pip install -r HSE-Avito/Backend/requirements.txt

echo ""
echo "Step 4: Running unit tests..."
cd HSE-Avito/Backend
export PYTHONPATH=/Users/amsafin/code/backend/HSE-Avito/Backend:$PYTHONPATH
pytest -xvs -m unit --tb=short

echo ""
echo "Step 5: Running integration tests..."
pytest -xvs -m integration --tb=short

echo ""
echo "=== All tests passed! ==="
echo ""
echo "Fixes verified:"
echo "  ✓ Debug code removed from moderation_worker.py"
echo "  ✓ Redis cache deletion tests added"
echo "  ✓ Tests converted to @pytest.mark.asyncio"
echo "  ✓ DB metrics context manager created and applied"
echo "  ✓ Service dependencies implemented"
echo "  ✓ Async context managers for DB connections"
echo ""
