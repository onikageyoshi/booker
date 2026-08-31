# =============================================================================
# Stage 1: Build dependencies
# =============================================================================
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.1.3

# Set working directory
WORKDIR /app

# Copy dependency files first (layer caching optimization)
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies, no virtualenv inside container)
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# =============================================================================
# Stage 2: Production image
# =============================================================================
FROM python:3.13-slim AS production

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r django && useradd -r -g django -d /app -s /sbin/nologin django

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy application code
COPY . .

# Collect static files
RUN DJANGO_SECRET_KEY=build-placeholder python manage.py collectstatic --noinput 2>/dev/null || true

# Ensure the non-root user owns the app directory
RUN chown -R django:django /app

# Switch to non-root user
USER django

# Expose the port Cloud Run expects
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/')" || exit 1

# Run with Gunicorn
# - bind: listen on 0.0.0.0:8080 (Cloud Run requirement)
# - workers: 2 * CPU + 1 (Cloud Run default is 1 vCPU)
# - timeout: 120s for cold starts
# - accesslog: log to stdout for Cloud Logging
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
