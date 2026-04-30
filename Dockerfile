# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies for pikepdf (QPDF) and WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libqpdf-dev \
    pkg-config \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqpdf29 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ src/
COPY pyproject.toml .
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/entrypoint.sh /usr/local/bin/siftpdf-entrypoint.sh

# Install the package itself, normalise the entrypoint, and create the
# non-root runtime user.
RUN pip install --no-cache-dir --no-deps . && \
    chmod +x /usr/local/bin/siftpdf-entrypoint.sh && \
    useradd --create-home siftpdf
USER siftpdf

EXPOSE 8000
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

# Default: run migrations then the API server (Railway sets $PORT dynamically).
CMD ["/usr/local/bin/siftpdf-entrypoint.sh"]
