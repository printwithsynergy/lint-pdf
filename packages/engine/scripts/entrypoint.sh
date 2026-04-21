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
set -eu

echo "[entrypoint] running alembic migrations"
alembic upgrade head

echo "[entrypoint] starting uvicorn on port ${PORT:-8000}"
exec uvicorn lintpdf.api.app:create_app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --factory
