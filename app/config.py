import os
import re
from dotenv import load_dotenv

load_dotenv()


def _coerce_to_pooler(url: str) -> str:
    """
    Rewrite a Supabase direct-connection URL to the IPv4-only transaction
    pooler endpoint.  Supabase pooler URLs are IPv4-only and designed for
    environments like Railway that lack IPv6 routing.

    Direct:  postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres
    Pooler:  postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres

    If DATABASE_URL is already a pooler URL (*.pooler.supabase.com) or is
    not a Supabase URL at all, it is returned unchanged.
    """
    # Already a pooler URL — nothing to do.
    if 'pooler.supabase.com' in url:
        return url

    # Match Supabase direct connection host: db.<project-ref>.supabase.co
    m = re.search(r'@db\.([a-z0-9]+)\.supabase\.co(:\d+)?/', url)
    if not m:
        return url  # Not a recognisable Supabase direct URL — leave alone.

    project_ref = m.group(1)

    # Allow the region to be overridden via env var; default to eu-west-2
    # which matches the project above. Set SUPABASE_REGION on Railway if yours differs.
    region = os.environ.get('SUPABASE_REGION', 'eu-west-2')
    pooler_host = f'aws-0-{region}.pooler.supabase.com'
    pooler_port = '6543'

    # Replace host[:port]
    url = re.sub(
        r'@db\.[a-z0-9]+\.supabase\.co(:\d+)?/',
        f'@{pooler_host}:{pooler_port}/',
        url,
    )

    # Pooler requires the user to be postgres.<project-ref>
    # Rewrite user portion: //postgres: → //postgres.<ref>:
    url = re.sub(
        r'(postgresql(?:\+psycopg2)?://)postgres:',
        rf'\1postgres.{project_ref}:',
        url,
    )

    # Ensure sslmode=require is present
    if 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url += f'{sep}sslmode=require'

    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # ── Database ───────────────────────────────────────────────────────────
    # DATABASE_URL is the single source of truth — no fallback, no SQLite.
    _database_url = os.environ.get('DATABASE_URL')
    if not _database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Set it to your Supabase PostgreSQL connection string."
        )

    # Railway / Heroku legacy compat: postgres:// → postgresql://
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)

    # Rewrite to Supabase pooler (IPv4-only) to avoid IPv6 failures on Railway.
    # If DATABASE_URL is already a pooler URL this is a no-op.
    _database_url = _coerce_to_pooler(_database_url)

    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── Redis ──────────────────────────────────────────────────────────────
    REDIS_URL = (
        os.environ.get('REDIS_URL')
        or os.environ.get('REDISURL')
        or 'redis://localhost:6379'
    )

    # ── Mail ───────────────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

    # ── Admin ──────────────────────────────────────────────────────────────
    ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
