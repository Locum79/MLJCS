import os
import re
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ── Load .env for local development ───────────────────────────────────────
load_dotenv()

# ── Ensure app package is importable ──────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── Alembic config object ──────────────────────────────────────────────────
config = context.config

# ── Logging ───────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── DATABASE_URL — single source of truth ─────────────────────────────────
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Alembic requires DATABASE_URL to be set to your Supabase PostgreSQL URL."
    )

# Normalise scheme
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# ── Coerce to Supabase pooler (IPv4-only) ─────────────────────────────────
# The direct Supabase host (db.<ref>.supabase.co:5432) resolves to IPv6 on
# Railway, which has no IPv6 routing.  The pooler endpoint is IPv4-only.
def _coerce_to_pooler(url: str) -> str:
    if 'pooler.supabase.com' in url:
        return url
    m = re.search(r'@db\.([a-z0-9]+)\.supabase\.co(:\d+)?/', url)
    if not m:
        return url
    project_ref = m.group(1)
    region = os.environ.get('SUPABASE_REGION', 'eu-west-2')
    pooler_host = f'aws-0-{region}.pooler.supabase.com'
    url = re.sub(
        r'@db\.[a-z0-9]+\.supabase\.co(:\d+)?/',
        f'@{pooler_host}:6543/',
        url,
    )
    url = re.sub(
        r'(postgresql(?:\+psycopg2)?://)postgres:',
        rf'\1postgres.{project_ref}:',
        url,
    )
    if 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url += f'{sep}sslmode=require'
    return url

database_url = _coerce_to_pooler(database_url)

# configparser treats % as interpolation — escape for set_main_option only
config.set_main_option('sqlalchemy.url', database_url.replace('%', '%%'))

# ── Import all models so autogenerate detects them ────────────────────────
from app.models import (  # noqa: F401
    Admin, OrgSettings, CertificateType, User,
    CertArchive, EmailDraft, Campaign, AuditLog, EmailLog,
)
from app import db  # noqa

target_metadata = db.metadata


# ── Migration runners ──────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
