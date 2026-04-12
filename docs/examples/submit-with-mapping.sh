#!/usr/bin/env bash
# Submit a PDF + a proprietary preflight report using a tenant-defined custom
# import mapping. See custom-mapping-xml.json / custom-mapping-json.json for
# the mapping configs themselves.
#
# Usage:
#   LINTPDF_API_KEY=lpdf_live_... ./submit-with-mapping.sh brochure.pdf report.xml <mapping_id>
#
# Positional args:
#   $1  PDF file                     (required)
#   $2  External report file         (required — XML or JSON per mapping.format)
#   $3  mapping_id (UUID)            (required — from /api/v1/tenant/import-mappings)
#
# Env vars:
#   LINTPDF_API_URL   default https://api.lintpdf.com
#   LINTPDF_API_KEY   required
#   LINTPDF_PROFILE   default lintpdf-default
set -euo pipefail

API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
: "${LINTPDF_API_KEY:?LINTPDF_API_KEY must be set}"
PROFILE="${LINTPDF_PROFILE:-lintpdf-default}"

PDF="${1:?path to PDF required}"
REPORT="${2:?path to external report required}"
MAPPING_ID="${3:?mapping_id (UUID) required}"

curl --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -F "file=@${PDF}" \
  -F "external_report=@${REPORT}" \
  -F "preflight_source=external" \
  -F "mapping_id=${MAPPING_ID}" \
  -F "profile_id=${PROFILE}"

# Note: mapping_id and external_format are mutually exclusive. If you set
# mapping_id, do NOT also send external_format — the API will reject the
# submission with 409.
