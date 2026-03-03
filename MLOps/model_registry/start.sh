#!/bin/bash
set -e

echo "=== Model Registry: Starting ==="

# 1. Поднимаем всё
echo "[1/3] Starting containers..."
docker compose up -d --build

# 2. Ждём postgres и запускаем миграции
echo "[2/3] Running migrations..."
docker compose exec app bash -c '
    export DB_HOST=postgres DB_PORT=5432 DB_USER=registry DB_PASSWORD=registry DB_NAME=model_registry
    bash migrate.sh
'

# 3. Готово
echo "[3/3] Done!"
echo ""
echo "  API:          http://localhost:8000"
echo "  Swagger UI:   http://localhost:8000/docs"
echo "  MinIO Console: http://localhost:9001  (minioadmin/minioadmin)"
echo ""
echo "=== Model Registry is running ==="