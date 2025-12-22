# ============================================
# STAGE 1: Builder - Install dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (only in builder stage)
# gcc: Required for compiling Python packages
# libpq-dev: PostgreSQL development headers for psycopg2
# postgresql-client: PostgreSQL client tools
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual env
RUN poetry config virtualenvs.create false

# Install dependencies (--no-root to skip installing the project itself)
RUN poetry install --no-interaction --no-ansi --no-root

# ============================================
# STAGE 2: Runtime - Production image
# ============================================
FROM python:3.12-slim

WORKDIR /app

# Install only runtime dependencies (no gcc!)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
