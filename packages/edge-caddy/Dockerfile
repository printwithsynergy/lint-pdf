FROM caddy:2.9-alpine

# Caddy reads the Caddyfile at /etc/caddy/Caddyfile by default.
COPY Caddyfile /etc/caddy/Caddyfile

# Expose 443 (TLS), 8080 (health), 8081 (internal ask proxy).
# Fly.io maps incoming 443 to container 443; 8080 is the health probe.
EXPOSE 443 8080 8081

# Default Caddy entrypoint runs ``caddy run --config /etc/caddy/Caddyfile``.
