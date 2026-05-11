import os
from dotenv import load_dotenv

load_dotenv()


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
