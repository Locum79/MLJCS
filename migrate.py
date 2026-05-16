import os
import sys
import re
import subprocess
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [MIGRATE] %(levelname)s %(message)s')
log = logging.getLogger(__name__)


def _redact(url: str) -> str:
    return re.sub('(:)[^:@]+(@)', '\\1***\\2', url)


def main():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        log.error('DATABASE_URL is not set.')
        sys.exit(1)
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = url
    log.info('DATABASE_URL: %s', _redact(url))
    if 'pooler.supabase.com' in url:
        log.info('✅ Using Supabase pooler endpoint (IPv4)')
    elif 'supabase.co' in url:
        log.warning('⚠️  Using DIRECT Supabase host — may fail on Railway (IPv6).')
        log.warning('    Set DATABASE_URL to the Transaction Pooler URL from:')
        log.warning('    Supabase Dashboard → Settings → Database → Connection Pooling')
    log.info('Running Alembic migrations…')
    try:
        result = subprocess.run(['python', '-m', 'alembic', 'upgrade', 'head'])
        if result.returncode != 0:
            log.error('Migrations FAILED (exit %d).', result.returncode)
            sys.exit(1)
    except FileNotFoundError:
        log.error("FATAL: 'alembic' binary not found on PATH. Verify alembic>=1.13.0 is in requirements.txt and was installed.")
        sys.exit(1)
    log.info('Migrations complete ✅')


if __name__ == '__main__':
    main()
