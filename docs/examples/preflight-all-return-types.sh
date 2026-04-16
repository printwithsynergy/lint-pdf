#!/usr/bin/env bash
# Submit a PDF for preflight with ALL checks (engine + AI + antivirus)
# and collect EVERY return type the API can produce.
#
# Usage:
#   LINTPDF_API_KEY=lpdf_live_... ./preflight-all-return-types.sh [pdf-file]
#
# Positional args:
#   $1  PDF file  (optional — defaults to the bundled test PDF)
#
# Env vars:
#   LINTPDF_API_URL   default https://api.lintpdf.com
#   LINTPDF_API_KEY   required
#   LINTPDF_PROFILE   default lintpdf-default
#   POLL_INTERVAL     seconds between status checks (default 10)
#   OUTPUT_DIR        directory for downloaded reports (default ./preflight-output)
#
# This script demonstrates all return types:
#   A. Job Response        — GET /api/v1/jobs/{job_id}
#   B. Report Formats      — POST /api/v1/jobs/{job_id}/reports
#      1. HTML             — Interactive hosted report
#      2. PDF              — Static PDF report
#      3. JSON             — Machine-readable JSON (LintPDF native schema)
#      4. XML              — XML report
#      5. annotated_pdf    — Original PDF with finding overlays (Scale+ plans)
#      6. annotated_pdf_markup — PDF with user annotations stamped (Scale+ plans)
#   C. Viewer API          — Interactive viewer data
#      7. Viewer Config    — GET /api/v1/viewer/jobs/{job_id}/config
#      8. Page Geometry    — GET /api/v1/viewer/jobs/{job_id}/pages
#      9. Page Tile (PNG)  — GET /api/v1/viewer/jobs/{job_id}/pages/{n}/tile
#     10. Separations      — GET /api/v1/viewer/jobs/{job_id}/separations
#   D. Token-based Public  — Public access via report tokens
#     11. Token Validation — GET /api/v1/reports/tokens/{token}
#     12. Token Findings   — GET /api/v1/reports/tokens/{token}/findings
#     13. Report List      — GET /api/v1/jobs/{job_id}/reports
#   E. Reference Data
#     14. Check Names      — GET /api/v1/check-names
set -euo pipefail

API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
: "${LINTPDF_API_KEY:?LINTPDF_API_KEY must be set}"
PROFILE="${LINTPDF_PROFILE:-lintpdf-default}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"
OUTPUT_DIR="${OUTPUT_DIR:-./preflight-output}"

PDF="${1:-}"
if [[ -z "$PDF" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  PDF="${SCRIPT_DIR}/../../packages/web/public/lintpdf_preflight_test_final.pdf"
fi

if [[ ! -f "$PDF" ]]; then
  echo "ERROR: PDF file not found: $PDF" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "============================================"
echo "  LintPDF — All Return Types Preflight"
echo "============================================"
echo "API:     $API_URL"
echo "Profile: $PROFILE"
echo "PDF:     $PDF"
echo "Output:  $OUTPUT_DIR"
echo ""

# -------------------------------------------------------------------
# Step 1: Submit preflight with all checks enabled
# -------------------------------------------------------------------
echo ">>> Step 1: Submitting preflight (engine + full AI scan)..."
echo "    ClamAV antivirus scan runs automatically on upload."
echo ""

SUBMIT_RESPONSE=$(curl -s --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -F "file=@${PDF}" \
  -F "profile_id=${PROFILE}" \
  -F "preflight_source=engine" \
  -F "ai_enabled=true" \
  -F "ai_preset=full-ai-scan")

JOB_ID=$(echo "$SUBMIT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "    Job submitted: $JOB_ID"
echo "    Antivirus: PASSED (upload accepted)"
echo "$SUBMIT_RESPONSE" | python3 -m json.tool > "$OUTPUT_DIR/01-submit-response.json"
echo "    Saved: $OUTPUT_DIR/01-submit-response.json"
echo ""

# -------------------------------------------------------------------
# Step 2: Poll for completion
# -------------------------------------------------------------------
echo ">>> Step 2: Waiting for job to complete..."
while true; do
  STATUS_RESPONSE=$(curl -s \
    "${API_URL}/api/v1/jobs/${JOB_ID}" \
    -H "Authorization: Bearer ${LINTPDF_API_KEY}")
  STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

  if [[ "$STATUS" == "complete" ]]; then
    echo "    Status: COMPLETE"
    break
  elif [[ "$STATUS" == "failed" ]]; then
    echo "    Status: FAILED"
    ERROR=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_message','unknown'))")
    echo "    Error: $ERROR"
    exit 1
  else
    echo "    Status: $STATUS (polling every ${POLL_INTERVAL}s)..."
    sleep "$POLL_INTERVAL"
  fi
done
echo ""

# -------------------------------------------------------------------
# Return Type A: Full Job Response
# -------------------------------------------------------------------
echo ">>> Return Type A: Job Response (findings + summary + scores)"
echo "$STATUS_RESPONSE" | python3 -m json.tool > "$OUTPUT_DIR/02-job-response.json"
echo "$STATUS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d.get('summary', {})
print(f'    Duration:     {d.get(\"duration_ms\", 0)}ms')
print(f'    Page Count:   {d.get(\"page_count\")}')
print(f'    Total:        {s.get(\"total_findings\", 0)} findings')
print(f'    Errors:       {s.get(\"error_count\", 0)}')
print(f'    Warnings:     {s.get(\"warning_count\", 0)}')
print(f'    Advisories:   {s.get(\"advisory_count\", 0)}')
print(f'    Passed:       {s.get(\"passed\")}')
print(f'    Color Grade:  {d.get(\"color_quality_grade\", \"N/A\")}')
print(f'    Color Score:  {d.get(\"color_quality_score\", \"N/A\")}')
findings = d.get('findings', [])
sources = {}
for f in findings:
    src = f.get('source', 'unknown')
    sources[src] = sources.get(src, 0) + 1
print(f'    By Source:    {sources}')
"
echo "    Saved: $OUTPUT_DIR/02-job-response.json"
echo ""

# -------------------------------------------------------------------
# Return Type B: Generate all report formats
# -------------------------------------------------------------------
echo ">>> Return Type B: Generating reports (html, pdf, json, xml, annotated_pdf, annotated_pdf_markup)..."
REPORTS_RESPONSE=$(curl -s --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs/${JOB_ID}/reports" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "formats": ["html", "pdf", "json", "xml", "annotated_pdf", "annotated_pdf_markup"],
    "detail_level": "comprehensive",
    "summary_page": "prepend",
    "allow_annotations": true
  }') || REPORTS_RESPONSE=$(curl -s --fail-with-body \
  -X POST "${API_URL}/api/v1/jobs/${JOB_ID}/reports" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "formats": ["html", "pdf", "json", "xml"],
    "detail_level": "comprehensive",
    "summary_page": "prepend",
    "allow_annotations": true
  }')

echo "$REPORTS_RESPONSE" | python3 -m json.tool > "$OUTPUT_DIR/03-reports-response.json"
echo "$REPORTS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('reports', []):
    print(f'    {r[\"format\"]:25s} {r[\"url\"]}')
"
echo "    Saved: $OUTPUT_DIR/03-reports-response.json"
echo ""

# Download each report
echo "    Downloading reports..."
echo "$REPORTS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('reports', []):
    fmt = r['format']
    url = r['url']
    token = r['token']
    print(f'{fmt}|{url}|{token}')
" | while IFS='|' read -r fmt url token; do
  ext="$fmt"
  case "$fmt" in
    html) ext="html" ;;
    annotated_pdf) ext="annotated.pdf" ;;
    annotated_pdf_markup) ext="markup.pdf" ;;
  esac
  outfile="$OUTPUT_DIR/report.$ext"
  curl -s -o "$outfile" "$url"
  size=$(wc -c < "$outfile")
  echo "    Downloaded: $outfile ($size bytes)"
done
echo ""

# -------------------------------------------------------------------
# Return Type C: Viewer API endpoints
# -------------------------------------------------------------------
echo ">>> Return Type C: Viewer API data"

# C.1 Viewer Config
echo "    C.1 Viewer Config..."
curl -s "${API_URL}/api/v1/viewer/jobs/${JOB_ID}/config" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" | python3 -m json.tool > "$OUTPUT_DIR/04-viewer-config.json"
echo "    Saved: $OUTPUT_DIR/04-viewer-config.json"

# C.2 Page Geometry
echo "    C.2 Page Geometry..."
curl -s "${API_URL}/api/v1/viewer/jobs/${JOB_ID}/pages" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" | python3 -m json.tool > "$OUTPUT_DIR/05-pages-geometry.json"
echo "    Saved: $OUTPUT_DIR/05-pages-geometry.json"

# C.3 Page Tile (PNG)
echo "    C.3 Page 1 Tile (PNG at 150 DPI)..."
curl -s -o "$OUTPUT_DIR/06-page1-tile.png" \
  "${API_URL}/api/v1/viewer/jobs/${JOB_ID}/pages/1/tile?dpi=150" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"
size=$(wc -c < "$OUTPUT_DIR/06-page1-tile.png")
echo "    Saved: $OUTPUT_DIR/06-page1-tile.png ($size bytes)"

# C.4 Separations
echo "    C.4 Ink Separations..."
curl -s "${API_URL}/api/v1/viewer/jobs/${JOB_ID}/separations" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" | python3 -m json.tool > "$OUTPUT_DIR/07-separations.json"
echo "    Saved: $OUTPUT_DIR/07-separations.json"
echo ""

# -------------------------------------------------------------------
# Return Type D: Token-based public access
# -------------------------------------------------------------------
echo ">>> Return Type D: Token-based public access"

# Extract HTML token from reports response
HTML_TOKEN=$(echo "$REPORTS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('reports', []):
    if r['format'] == 'html':
        print(r['token'])
        break
")

if [[ -n "$HTML_TOKEN" ]]; then
  # D.1 Token Validation
  echo "    D.1 Token Validation..."
  curl -s "${API_URL}/api/v1/reports/tokens/${HTML_TOKEN}" | python3 -m json.tool > "$OUTPUT_DIR/08-token-validation.json"
  echo "    Saved: $OUTPUT_DIR/08-token-validation.json"

  # D.2 Token Findings
  echo "    D.2 Token Findings (public viewer access)..."
  curl -s "${API_URL}/api/v1/reports/tokens/${HTML_TOKEN}/findings" | python3 -m json.tool > "$OUTPUT_DIR/09-token-findings.json"
  FINDING_COUNT=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/09-token-findings.json')); print(len(d.get('findings',[])))")
  echo "    Saved: $OUTPUT_DIR/09-token-findings.json ($FINDING_COUNT findings)"
fi

# D.3 Report Token List
echo "    D.3 Report Token List..."
curl -s "${API_URL}/api/v1/jobs/${JOB_ID}/reports" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" | python3 -m json.tool > "$OUTPUT_DIR/10-report-tokens.json"
echo "    Saved: $OUTPUT_DIR/10-report-tokens.json"
echo ""

# -------------------------------------------------------------------
# Return Type E: Reference data
# -------------------------------------------------------------------
echo ">>> Return Type E: Reference data"
echo "    E.1 Check Name Registry..."
curl -s "${API_URL}/api/v1/check-names" | python3 -m json.tool > "$OUTPUT_DIR/11-check-names.json"
CHECK_COUNT=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/11-check-names.json')); print(len(d))")
echo "    Saved: $OUTPUT_DIR/11-check-names.json ($CHECK_COUNT registered checks)"
echo ""

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
echo "============================================"
echo "  All return types collected!"
echo "============================================"
echo ""
echo "Files in $OUTPUT_DIR:"
ls -lh "$OUTPUT_DIR/"
echo ""
echo "Report URLs:"
echo "$REPORTS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('reports', []):
    print(f'  {r[\"format\"]:25s} {r[\"url\"]}')
"
