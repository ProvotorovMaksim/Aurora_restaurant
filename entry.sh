#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
# Ждем, пока PostgreSQL станет доступен (максимум 30 секунд)
for i in {1..30}; do
  if python -c "import asyncio; import asyncpg; from settings import settings; asyncio.run(asyncpg.connect(user=settings.DB_USER, password=settings.DB_PASSWORD, database=settings.DB_NAME, host=settings.DB_HOST, port=settings.DB_PORT))" 2>/dev/null; then
    echo "PostgreSQL is ready!"
    break
  fi
  echo "PostgreSQL is unavailable - sleeping ($i/30)"
  if [ "$i" -eq 30 ]; then
    echo "PostgreSQL did not become available in time."
    exit 1
  fi
  sleep 1
done

echo "Running database migrations..."
# Применяем все миграции до последней версии
alembic upgrade head

echo "Starting FastAPI application..."
# Запускаем приложение
exec uvicorn main:app --host 0.0.0.0 --port 8001