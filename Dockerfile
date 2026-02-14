# Finding 18: Pin base image by digest
FROM python:3.13-slim@sha256:3de9a8d7aedbb7984dc18f2dff178a7850f16c1ae7c34ba9d7ecc23d0755e35f

WORKDIR /app

# Finding 17: psycopg2 (not -binary) needs libpq-dev + gcc
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -r -u 1000 -s /sbin/nologin appuser

# Create writable dirs for server-side sessions, rate limiter, and tmp
RUN mkdir -p /tmp/flask_sessions /tmp/flask_limiter && \
    chown -R appuser:appuser /tmp/flask_sessions /tmp/flask_limiter

COPY app/ app/

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:create_app()"]
