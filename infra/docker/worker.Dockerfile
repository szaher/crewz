# Worker Dockerfile for Celery Workers
# Extends backend image with worker-specific dependencies and configuration

# Use backend image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gevent for worker pool
RUN pip install --no-cache-dir gevent==23.9.1

# Copy application code
COPY backend/src /app/src

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Resource limits (applied via docker-compose/k8s)
# CPU: 2 cores
# Memory: 4GB

# Health check - verify worker is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD celery -A src.workers.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Default command: Start Celery worker with gevent pool
# --concurrency=4: Handle 4 tasks concurrently per worker
# --pool=gevent: Use gevent for async I/O
# --loglevel=info: Info-level logging
# --max-tasks-per-child=1000: Restart worker after 1000 tasks (prevent memory leaks)
CMD ["celery", "-A", "src.workers.celery_app", "worker", \
     "--concurrency=4", \
     "--pool=gevent", \
     "--loglevel=info", \
     "--max-tasks-per-child=1000", \
     "--time-limit=3600", \
     "--soft-time-limit=3000"]
