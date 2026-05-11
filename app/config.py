import os
import re
from dotenv import load_dotenv

load_dotenv()


def _to_pooler(url: str) -> str:
    """
    Always convert a Supabase direct-connection URL to the transaction pooler.
    The pooler endpoint is IPv4-only; the direct host resolves IPv6 on Railway.

    If the URL is already a pooler URL, or is not Supabase at all, it is
    returned unchanged.
    """
    if not url:
        return url
    # Already pooler — nothing to do
    if 'pooler.supabase.com' in url:
        return url
    # Only rewrite known Supabase direct hosts
    m = re.search(r'@db\.([a-z0-9]+)\.supabase\.co(?::\d+)?/', url)
    if not m:
        return url

    ref = m.group(1)
    # Region: honour explicit env var, otherwise derive from Supabase metadata
    # eu-central-1 is confirmed correct for this project
    region = os.environ.get('SUPABASE_REGION', 'eu-central-1')
    pooler = f'aws-0-{region}.pooler.supabase.com'

    # 1. Swap host + port
    url = re.sub(
        r'@db\.[a-z0-9]+\.supabase\.co(?::\d+)?/',
        f'@{pooler}:6543/',
        url,
    )
    # 2. Pooler user must be postgres.<ref> (not bare postgres)
    url = re.sub(
        r'(postgresql(?:\+psycopg2)?://)postgres(?!\.)(:)',
        rf'\1postgres.{ref}\2',
        url,
    )
    # 3. Ensure sslmode=require
    if 'sslmode=' not in url:
        url += ('&' if '?' in url else '?') + 'sslmode=require'

    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # ── Database ───────────────────────────────────────────────────────────
    _url = os.environ.get('DATABASE_URL', '')
    if not _url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Configure it in Railway → Variables."
        )

    # Normalise legacy scheme
    if _url.startswith('postgres://'):
        _url = _url.replace('postgres://', 'postgresql://', 1)

    # Force pooler endpoint — safe no-op if already a pooler URL
    _url = _to_pooler(_url)

    SQLALCHEMY_DATABASE_URI = _url
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
