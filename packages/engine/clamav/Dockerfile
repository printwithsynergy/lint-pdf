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
#
# StreamMaxLength 1G: the upstream clamd default + the Railway sidecar's
# default both leave this unset / set to 0, which in clamd's INSTREAM
# protocol means "reject every stream" (observed in production logs as
# "INSTREAM: Size limit reached, (requested: 1024, max: 0)"). Every
# scan fails, the engine fail-opens, and setting LINTPDF_CLAMAV_REQUIRED=1
# would 503 every upload. Baking 1G here matches the engine's per-tenant
# max_file_size_mb ceiling with plenty of headroom.
#
# MaxFileSize / MaxScanSize keep the individual-file / per-scan memory
# caps aligned so clamd doesn't OOM its container on a pathologically
# large upload.
RUN set -eux; \
    CONF=/etc/clamav/clamd.conf; \
    test -f "$CONF"; \
    printf '\n# LintPDF: TCP listener + INSTREAM caps baked in by Dockerfile\nTCPSocket 3310\nTCPAddr 0.0.0.0\nStreamMaxLength 1G\nMaxFileSize 1G\nMaxScanSize 1G\n' >> "$CONF"; \
    grep -q '^TCPSocket 3310' "$CONF"; \
    grep -q '^TCPAddr 0.0.0.0' "$CONF"; \
    grep -q '^StreamMaxLength 1G' "$CONF"; \
    grep -q '^MaxFileSize 1G' "$CONF"; \
    grep -q '^MaxScanSize 1G' "$CONF"

EXPOSE 3310

# Base image already ENTRYPOINTs at s6-overlay's /init — no override needed.
