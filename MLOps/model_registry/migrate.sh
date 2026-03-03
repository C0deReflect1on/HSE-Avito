#!/bin/bash
set -e

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-registry}"
DB_PASSWORD="${DB_PASSWORD:-registry}"
DB_NAME="${DB_NAME:-model_registry}"

export PGPASSWORD="$DB_PASSWORD"

echo "Waiting for PostgreSQL..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
    sleep 1
done

echo "Running migrations..."
for f in migrations/*.sql; do
    echo "Applying $f..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$f"
done

echo "Migrations done."