# Viddash - Production Dockerfile
# Python slim + FFmpeg, runs Gunicorn

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Install ffmpeg and runtime deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -ms /bin/bash appuser
WORKDIR /app

# Install Python deps first (better caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app

# Ensure runtime directories exist and ownership
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Gunicorn config file is provided separately
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
