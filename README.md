# CertifyStack

Certificate generation and dispatch platform for Medical Locum Jobs.

## Railway Deployment

1. Fork this repo to your GitHub
2. On Railway: New Project → Deploy from GitHub repo
3. Add services: PostgreSQL + Redis
4. Set environment variables (see below)
5. Run setup: `python setup_railway.py` in Railway shell
6. Login at `/login` with ADMIN_EMAIL and ADMIN_PASSWORD

## Required Railway Env Vars

```
SECRET_KEY=random-string-32-chars
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-gmail-app-password
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-password
```

DATABASE_URL and REDIS_URL are auto-set by Railway.

## Local Dev

```bash
pip install -r requirements.txt
flask run
```
