#!/bin/sh
# MLJCS Production Startup Script
echo "Starting Production Migrations..."
python migrate.py

echo "Launching Application..."
gunicorn --bind 0.0.0.0:${PORT:-8080} wsgi:app
