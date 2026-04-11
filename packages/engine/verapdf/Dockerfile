# LintPDF veraPDF sidecar — PDF/A validation service.
#
# Uses the official veraPDF REST image. The /api/info endpoint serves as
# the Railway healthcheck so sleep/wake works correctly.
#
# Usage:
#   Railway dashboard -> Engine service -> Env vars:
#     LINTPDF_VERAPDF_URL=http://verapdf.railway.internal:8080

FROM verapdf/rest:latest

EXPOSE 8080

# The base image already has an ENTRYPOINT that starts the REST server.
# JAVA_OPTS can be set via Railway env vars if needed (default: -Xmx512m).
