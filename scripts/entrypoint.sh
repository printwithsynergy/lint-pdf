#!/bin/sh
# Engine runtime entrypoint.
#
# Runs pending Alembic migrations before handing control to uvicorn.
# If the database schema already exists (e.g. restored from a dump) but
# the alembic_version table is missing or incomplete, ``alembic upgrade head``
# can fail with DuplicateObject. In that case we fall back to ``alembic stamp
# head`` which marks all migrations as applied without re-running DDL.
set -eu

echo "[entrypoint] running alembic migrations"
if ! alembic upgrade head 2>&1; then
    echo "[entrypoint] upgrade failed — attempting schema-exists recovery via stamp head"
    alembic stamp head
    echo "[entrypoint] stamp complete, proceeding with startup"
fi

WORKERS="${LINTPDF_WORKERS:-4}"
CONCURRENCY="${LINTPDF_CONCURRENCY_PER_WORKER:-20}"

echo "[entrypoint] starting uvicorn on port ${PORT:-8000} (workers=${WORKERS} concurrency=${CONCURRENCY})"
exec uvicorn lintpdf.api.app:create_app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --factory \
    --workers "${WORKERS}" \
    --limit-concurrency "${CONCURRENCY}" \
    --timeout-keep-alive 5
