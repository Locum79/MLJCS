#!/usr/bin/env python
"""
Production migration runner.
Called by start.sh before gunicorn boots.
Exits non-zero on failure so Railway aborts the deploy.
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
    if not os.environ.get('DATABASE_URL'):
        log.error("DATABASE_URL is not set — cannot run migrations.")
        sys.exit(1)

    log.info("Running Alembic migrations…")
    result = subprocess.run(['alembic', 'upgrade', 'head'])

    if result.returncode != 0:
        log.error("Migrations FAILED (exit %d). Aborting deployment.", result.returncode)
        sys.exit(1)

    log.info("Migrations complete ✅")


if __name__ == '__main__':
    main()
