#!/usr/bin/env python
"""
Production migration runner — forces IPv4 to avoid Railway/Docker IPv6 issues.
Called by start.sh before gunicorn.
"""
import os
import sys
import socket
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MIGRATE] %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)

# ── Force IPv4: Railway containers often lack IPv6 routes, but DNS may
# resolve Supabase to an IPv6 address first, causing instant failure.
_orig_getaddrinfo = socket.getaddrinfo

def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    results = _orig_getaddrinfo(host, port, family, type, proto, flags)
    ipv4 = [r for r in results if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else results  # fall back to whatever exists

socket.getaddrinfo = _ipv4_only
log.info("IPv4-only socket patch applied.")


def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        log.error("DATABASE_URL is not set — cannot run migrations.")
        sys.exit(1)

    log.info("Running Alembic migrations against Supabase PostgreSQL…")
    result = subprocess.run(['alembic', 'upgrade', 'head'])

    if result.returncode != 0:
        log.error("Alembic migrations FAILED (exit code %d). Aborting.", result.returncode)
        sys.exit(1)

    log.info("Migrations complete ✅")


if __name__ == '__main__':
    main()
