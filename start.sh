#!/bin/sh

# Halt the startup execution chain if any individual command fails
set -e

echo "Running asynchronous database migrations via uv..."
uv run alembic upgrade head

echo "Starting FastAPI Production Server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
