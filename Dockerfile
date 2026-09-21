# Faith-n-Action / KofC Management System — production image
# NOTE: requires the packages in requirements-prod.txt (gunicorn etc.),
# which are PENDING APPROVAL per GLOBAL_AGENTS.MD G2 — do not build until
# requirements-prod.txt is approved and merged into the image.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for Pillow (image validation) and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt -r requirements-prod.txt

COPY . .

# Runtime artifacts are created at container start, never baked in:
#   - private/public RSA keys must be mounted as secrets (see docker-compose.yml)
#   - db.sqlite3 lives on a volume (dev) or use PostgreSQL via DATABASE_URL (prod)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# migrate at start (idempotent), then gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn -c deploy/gunicorn.conf.py base.wsgi:application"]
