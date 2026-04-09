# LintPDF ClamAV sidecar
#
# This image exists as a permanent replacement for the broken
# thinkneverland/railway-clamav sidecar, which runs configure-env.sh at
# BUILD time so Railway's runtime CLAMD_CONF_* env vars are silently
# ignored. In that image, clamd never opens its TCP listener because the
# config file is written during `docker build` (when those env vars don't
# exist yet) rather than at container start.
#
# Production today uses a runtime startCommand override on the ClamAV
# service that patches clamd.conf and then execs /init. That works but
# depends on Railway-side service configuration that is easy to lose. If
# the startCommand ever gets cleared or the upstream image changes,
# Railway can be repointed at this directory instead:
#
#   Railway Settings -> Source -> Repo=thinkneverland/lint-pdf,
#   Branch=main, Root Directory=packages/engine/clamav
#
# Then remove the startCommand override and clear the throwaway
# CLAMD_CONF_* env vars.

FROM clamav/clamav:stable

# clamav/clamav:stable ships clamd.conf under /etc/clamav/. Bake the TCP
# listener directly so there's no runtime env-var dependency. The trailing
# grep -q assertions fail the build if the append didn't land, catching
# any future base-image layout changes immediately.
RUN set -eux; \
    CONF=/etc/clamav/clamd.conf; \
    test -f "$CONF"; \
    printf '\n# LintPDF: TCP listener baked in by Dockerfile\nTCPSocket 3310\nTCPAddr 0.0.0.0\n' >> "$CONF"; \
    grep -q '^TCPSocket 3310' "$CONF"; \
    grep -q '^TCPAddr 0.0.0.0' "$CONF"

EXPOSE 3310

# Base image already ENTRYPOINTs at s6-overlay's /init — no override needed.
