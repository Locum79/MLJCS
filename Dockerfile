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

EXPOSE 8080

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120"]
