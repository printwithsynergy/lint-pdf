# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies for pikepdf (QPDF) and WeasyPrint.
# git is needed because the `siftpdf` dep is a git+https reference
# (see pyproject.toml — Phase 4 Stage C).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libqpdf-dev \
    pkg-config \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/engine/pyproject.toml .
# GITHUB_TOKEN is required to clone the private thinkneverland/sift-pdf
# repo. Railway passes it as a build arg (configured via
# `railway variables --set "GITHUB_TOKEN=..."` on the engine service).
# Until visibility flips public, this is mandatory at build time.
ARG GITHUB_TOKEN
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -n "$GITHUB_TOKEN" ]; then \
        git config --global url."https://oauth2:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi && \
    pip install --no-cache-dir . && \
    git config --global --unset url."https://oauth2:${GITHUB_TOKEN}@github.com/".insteadOf || true

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
COPY packages/engine/src/ src/
COPY packages/engine/pyproject.toml .
COPY packages/engine/alembic/ alembic/
COPY packages/engine/alembic.ini .
COPY packages/engine/scripts/entrypoint.sh /usr/local/bin/lintpdf-entrypoint.sh

# Install the package itself, normalise the entrypoint, and create the
# non-root runtime user.
RUN pip install --no-cache-dir --no-deps . && \
    chmod +x /usr/local/bin/lintpdf-entrypoint.sh && \
    useradd --create-home lintpdf
USER lintpdf

EXPOSE 8000
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

# Default: run migrations then the API server (Railway sets $PORT dynamically).
CMD ["/usr/local/bin/lintpdf-entrypoint.sh"]
