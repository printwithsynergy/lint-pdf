#!/bin/sh
# Engine runtime entrypoint.
#
# Runs pending Alembic migrations before handing control to uvicorn. We
# migrate on every boot so a newly-deployed image never serves traffic
# against a schema it doesn't expect. ``alembic upgrade head`` is a
# no-op when the database is already up to date, so the steady-state
# cost is a single metadata query.
#
# Railway redeploys one instance at a time; for a multi-replica
# deployment the first instance takes the implicit PG advisory lock that
# ``alembic`` grabs around its upgrade, while subsequent instances wait
# a beat and then find the migration already applied.
#
# Worker sizing: we run multiple Uvicorn worker processes so a single
# slow or CPU-bound request (large PDF upload, alembic migration from a
# sibling replica, etc.) cannot monopolize the event loop and starve
# /ready health checks. A single-worker deploy wedged under 15 parallel
# ~30 MB uploads on 2026-04-21 — Railway health-check-killed the
# container, producing ~44 min of log silence. See
# preflight-stress-results.md for the incident write-up.
#
# LINTPDF_WORKERS (default 4) is tuned so 2 vCPU Railway containers can
# still accept control-plane calls (/ready, /api/v1/admin/*) while a
# burst of uploads consumes the other workers.
#
# LINTPDF_CONCURRENCY_PER_WORKER (default 20) caps in-flight async
# handlers per worker. Past this cap Uvicorn responds with 503 rather
# than queueing, which shifts back-pressure to clients (who retry with
# exponential backoff) instead of exhausting container memory.
set -eu

echo "[entrypoint] running alembic migrations"
alembic upgrade head

WORKERS="${LINTPDF_WORKERS:-4}"
CONCURRENCY="${LINTPDF_CONCURRENCY_PER_WORKER:-20}"

echo "[entrypoint] starting uvicorn on port ${PORT:-8000} (workers=${WORKERS} concurrency=${CONCURRENCY})"
exec uvicorn siftpdf.api.app:create_app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --factory \
    --workers "${WORKERS}" \
    --limit-concurrency "${CONCURRENCY}" \
    --timeout-keep-alive 5
