# Reels Maker — container image
FROM python:3.12-slim

# system deps: ffmpeg (video/audio), opencv + ctranslate2 runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps age (layer cache — code palta gele o deps rebuild hoy na)
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# app code
COPY engine ./engine

ENV REELS_HOST=0.0.0.0 \
    REELS_PORT=5000 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models

EXPOSE 5000

# gunicorn: 1 worker (JOBS in-memory share), threads for concurrency, long timeout for uploads
CMD ["gunicorn", "--chdir", "engine/web", "app:app", \
     "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "3600"]
