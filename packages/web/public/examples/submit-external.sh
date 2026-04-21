#!/usr/bin/env bash
# Submit a PDF plus an existing preflight report (external mode).
#
# Usage:
#   LINTPDF_API_KEY=lpdf_live_... ./submit-external.sh brochure.pdf pitstop-report.xml pitstop_xml
#
# Positional args:
#   $1  PDF file                            (required)
#   $2  External report file                (required)
#   $3  external_format                     (optional — omit to auto-detect)
#         One of: pitstop_xml, callas_json, callas_xml, acrobat_xml, lintpdf_json
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
FORMAT="${3:-}"

args=(
  -X POST "${API_URL}/api/v1/jobs"
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"
  -F "file=@${PDF}"
  -F "external_report=@${REPORT}"
  -F "preflight_source=external"
  -F "profile_id=${PROFILE}"
)

if [[ -n "${FORMAT}" ]]; then
  args+=(-F "external_format=${FORMAT}")
fi

curl --fail-with-body "${args[@]}"
