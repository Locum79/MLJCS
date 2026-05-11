#!/usr/bin/env python
"""
Production migration runner.
Called before gunicorn starts: `python migrate.py && gunicorn wsgi:app ...`

Exit codes:
  0 — migrations applied (or already up to date)
  1 — migration failed (deployment will abort on Railway)
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MIGRATE] %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)


def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        log.error("DATABASE_URL is not set — cannot run migrations.")
        sys.exit(1)

    log.info("Running Alembic migrations against Supabase PostgreSQL…")
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        capture_output=False,   # let stdout/stderr pass through to Railway logs
    )

    if result.returncode != 0:
        log.error("Alembic migrations FAILED (exit code %d). Aborting deployment.", result.returncode)
        sys.exit(1)

    log.info("Migrations complete ✅")


if __name__ == '__main__':
    main()
