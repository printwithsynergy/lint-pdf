#!/usr/bin/env bash
# Submit a PDF with anonymous / unbranded output forced on for this single
# submission. The tenant's branding default is ignored for this job only.
#
# What "anonymous" strips:
#   - tenant logos, header text, and brand colors from every report
#   - LintPDF wordmark and any "Powered by LintPDF" affordances
#   - PDF metadata (Author / Producer / Creator) sanitized on generated reports
#   - neutral filename: preflight-<short-id>.pdf (no tenant slug)
#   - viewer chrome branding and share-page chrome
#
# Usage:
#   LINTPDF_API_KEY=lpdf_live_... ./submit-anonymous.sh brochure.pdf
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

curl --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -F "file=@${PDF}" \
  -F "profile_id=${PROFILE}" \
  -F "brand=anonymous"

# Tip: to make anonymous the default for every job in this tenant, PATCH
# /api/v1/tenant/branding-defaults with {"mode": "anonymous"} instead of
# setting brand=anonymous per-request. Per-request always wins over the
# tenant default. Share links mint their branding at creation time and are
# immutable — a share link minted from an anonymous run stays anonymous even
# if the tenant default flips back to branded later.
