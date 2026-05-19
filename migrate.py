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
    
    # Run post-migration DB sanitization for PNG templates and OBS course
    sanitize_coordinates()


def sanitize_coordinates():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        return
    log.info("Sanitizing certificate database coordinates...")
    
    obs_coords = {
        'name_x': 395.73,
        'name_y': 330.0,
        'name_w': 600.0,
        'name_h': 50,
        'name_font_size': 32,
        'name_align': 'center',
        'name_color': '#111111',
        
        'date_x': 395.73,
        'date_y': 205.0,
        'date_font_size': 12,
        'date_align': 'center',
        
        'cert_id_x': 585.0,
        'cert_id_y': 70.0,
        'cert_id_font_size': 11,
        
        'qr_x': 40,
        'qr_y': 40,
        'qr_size': 85,
        'mask_color': 'transparent'
    }
    
    import json
    
    # Try PostgreSQL first
    if url.startswith('postgresql://') or url.startswith('postgres://'):
        try:
            import psycopg2
            conn = psycopg2.connect(url)
            cur = conn.cursor()
            cur.execute(
                "UPDATE certificate_types SET overlay_coords = %s WHERE course_code = 'OBS' OR master_file_type = 'png'",
                (json.dumps(obs_coords),)
            )
            conn.commit()
            log.info(f"Successfully sanitized coordinates in PostgreSQL database! Row count: {cur.rowcount}")
            cur.close()
            conn.close()
        except Exception as e:
            log.error(f"PostgreSQL coordinates sanitization failed: {e}")
            
    # Try SQLite next (for local/testing DBs)
    elif os.path.exists("instance/test.db") or 'test.db' in url:
        try:
            import sqlite3
            conn = sqlite3.connect("instance/test.db")
            cur = conn.cursor()
            cur.execute(
                "UPDATE certificate_types SET overlay_coords = ? WHERE course_code = 'OBS' OR master_file_type = 'png'",
                (json.dumps(obs_coords),)
            )
            conn.commit()
            log.info(f"Successfully sanitized coordinates in SQLite database! Row count: {cur.rowcount}")
            cur.close()
            conn.close()
        except Exception as e:
            log.error(f"SQLite coordinates sanitization failed: {e}")


if __name__ == '__main__':
    main()
