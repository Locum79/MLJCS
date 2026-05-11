FROM python:3.11-slim

WORKDIR /app

# System deps: tesseract for OCR, libgl for opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

# Force system-level IPv4 preference so libpq/psycopg2 never picks IPv6.
# Railway containers lack IPv6 routing; Supabase DNS returns both A + AAAA.
RUN echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf

EXPOSE 8080

# start.sh runs migrations at container startup (runtime), then launches gunicorn.
# Migrations must NOT run during build — the DB is unreachable then.
CMD ["sh", "start.sh"]
