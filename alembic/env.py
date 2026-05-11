import os
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

# ── DATABASE_URL — single source of truth, no fallback ────────────────────
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Alembic requires DATABASE_URL to be set to your Supabase PostgreSQL URL."
    )

# Railway / Heroku legacy compat: postgres:// → postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# configparser interprets % as interpolation syntax — escape all % signs.
config.set_main_option('sqlalchemy.url', database_url.replace('%', '%%'))

# ── Import all models so autogenerate detects them ────────────────────────
from app.models import (  # noqa: F401, E402
    Admin,
    OrgSettings,
    CertificateType,
    User,
    CertArchive,
    EmailDraft,
    Campaign,
    AuditLog,
    EmailLog,
)
from app import db  # noqa: E402

target_metadata = db.metadata


# ── Migration runners ──────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (outputs SQL)."""
    url = database_url  # use the raw URL, not the configparser-escaped version
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
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
