#!/usr/bin/env python
"""Production migration runner."""
import os
import sys
import re
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MIGRATE] %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)


def _to_pooler(url: str) -> str:
    if not url or 'pooler.supabase.com' in url:
        return url
    m = re.search(r'@db\.([a-z0-9]+)\.supabase\.co(?::\d+)?/', url)
    if not m:
        return url
    ref = m.group(1)
    region = os.environ.get('SUPABASE_REGION', 'eu-central-1')
    pooler = f'aws-0-{region}.pooler.supabase.com'
    url = re.sub(r'@db\.[a-z0-9]+\.supabase\.co(?::\d+)?/', f'@{pooler}:6543/', url)
    url = re.sub(r'(postgresql(?:\+psycopg2)?://)postgres(?!\.)(:)', rf'\1postgres.{ref}\2', url)
    if 'sslmode=' not in url:
        url += ('&' if '?' in url else '?') + 'sslmode=require'
    return url


def _redact(url: str) -> str:
    return re.sub(r'(:)[^:@]+(@)', r'\1***\2', url)


def main():
    raw = os.environ.get('DATABASE_URL', '')
    if not raw:
        log.error("DATABASE_URL is not set.")
        sys.exit(1)

    if raw.startswith('postgres://'):
        raw = raw.replace('postgres://', 'postgresql://', 1)

    pooler_url = _to_pooler(raw)
    log.info("DATABASE_URL in:  %s", _redact(raw))
    log.info("Connecting via:   %s", _redact(pooler_url))

    # Set the (possibly rewritten) URL back so Alembic env.py picks it up
    os.environ['DATABASE_URL'] = pooler_url

    log.info("Running Alembic migrations…")
    result = subprocess.run(['alembic', 'upgrade', 'head'])

    if result.returncode != 0:
        log.error("Migrations FAILED (exit %d).", result.returncode)
        if 'pooler.supabase.com' in pooler_url:
            log.error(
                "If you see 'Tenant or user not found': go to Supabase Dashboard "
                "→ Settings → Database → Connection Pooling and verify the pooler "
                "is ENABLED and copy the exact Transaction Pooler URL into "
                "DATABASE_URL on Railway."
            )
        sys.exit(1)

    log.info("Migrations complete ✅")


if __name__ == '__main__':
    main()
