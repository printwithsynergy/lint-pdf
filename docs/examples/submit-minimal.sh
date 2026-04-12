#!/usr/bin/env bash
# Submit a PDF in minimal (viewer-only) mode — no analyzers run on ingest.
#
# Minimal mode is the cheapest path to a rendered viewer. Page geometry is
# computed immediately; deeper capabilities (separations, TAC, fonts, images)
# load on demand when a reviewer clicks the corresponding "Load" affordance in
# the viewer.
#
# Usage:
#   LINTPDF_API_KEY=lpdf_live_... ./submit-minimal.sh brochure.pdf
#
# Env vars:
#   LINTPDF_API_URL   default https://api.lintpdf.com
#   LINTPDF_API_KEY   required
set -euo pipefail

API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
: "${LINTPDF_API_KEY:?LINTPDF_API_KEY must be set}"

PDF="${1:?path to PDF required}"

curl --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -F "file=@${PDF}" \
  -F "preflight_source=minimal"
