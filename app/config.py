import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///certifystack.db')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    
    REDIS_URL = os.environ.get('REDIS_URL') or os.environ.get('REDISURL') or 'redis://localhost:6379'
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
