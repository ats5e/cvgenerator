FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CHROME_PATH=/usr/bin/chromium

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-dejavu-core \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["/bin/sh", "-c", "gunicorn --workers=1 --threads=4 --timeout=180 --bind=0.0.0.0:${PORT:-10000} app:app"]
