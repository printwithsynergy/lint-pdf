# Thin passthrough to the upstream edoburu/pgbouncer image. Railway's
# Dockerfile builder needs a local Dockerfile even when we're just
# lifting an upstream image verbatim. We re-declare ENV defaults here
# for documentation — all are overridable via the service's env vars.
#
# Bulk-files step 7 — see railway.toml in this directory for the
# connection-pool rationale.

FROM edoburu/pgbouncer:latest

# Defaults; every one is overridable from the Railway service
# variables (see Worker-AI / control-plane patterns in this repo).
ENV POOL_MODE=transaction \
    MAX_CLIENT_CONN=500 \
    DEFAULT_POOL_SIZE=30 \
    RESERVE_POOL_SIZE=5 \
    SERVER_LIFETIME=3600 \
    SERVER_IDLE_TIMEOUT=600 \
    AUTH_TYPE=scram-sha-256 \
    LISTEN_PORT=6432

EXPOSE 6432
