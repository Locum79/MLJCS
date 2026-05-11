#!/bin/sh
set -e

echo "==> Running Alembic migrations..."
python migrate.py

echo "==> Starting gunicorn..."
exec gunicorn wsgi:app --bind "0.0.0.0:${PORT:-8080}" --workers 1 --timeout 120
