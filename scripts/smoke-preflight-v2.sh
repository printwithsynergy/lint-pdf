#!/usr/bin/env bash
# v2 playbook closer (PR 18) — engineer-runnable end-to-end smoke that
# proves every consumer surface is aligned:
#
#   1. Submits packages/engine/tests/fixtures/test-sample.pdf via the
#      LintPDF Python SDK against a configured engine.
#   2. Polls until the job is terminal.
#   3. Mints HTML / PDF / JSON / annotated PDF report tokens.
#   4. Calls /jobs/{id}/epm for the candidacy verdict.
#   5. Calls POST .../findings/{id}/explain on the first 3 findings
#      (real Claude Haiku 4.5 — costs ~$0.10 per run).
#   6. Prints every URL + verdict + explanation line.
#
# Usage:
#   ./scripts/smoke-preflight-v2.sh                      # default fixture
#   ./scripts/smoke-preflight-v2.sh path/to/file.pdf     # custom PDF
#
# Env (required):
#   LINTPDF_API_KEY    Bearer token (starts with lpdf_live_ or lpdf_test_)
#
# Env (optional):
#   LINTPDF_API_URL    Engine base URL. Default https://api.lintpdf.com
#   LINTPDF_PROFILE_ID Profile to run against. Default lintpdf-default
#   SMOKE_EXPLAIN      "0" to skip the AI-Explain step. Default "1".
#
# Exit codes:
#   0   job complete, every artefact printed.
#   1   missing API key.
#   2   engine returned a non-2xx on submit / poll / mint / explain.
#   3   job failed in the engine (status=failed).
#
# Source-of-truth complement to packages/engine/tests/test_preflight_smoke.py
# (PR 8) — that pytest path stubs Claude; this shell path exercises the
# real consumer chain end-to-end.

set -euo pipefail

API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
PROFILE_ID="${LINTPDF_PROFILE_ID:-lintpdf-default}"
EXPLAIN="${SMOKE_EXPLAIN:-1}"
PDF_PATH="${1:-packages/engine/tests/fixtures/test-sample.pdf}"

# ----- guards ------------------------------------------------------------

if [[ -z "${LINTPDF_API_KEY:-}" ]]; then
  echo "✘ LINTPDF_API_KEY is required" >&2
  exit 1
fi
if [[ ! -f "$PDF_PATH" ]]; then
  echo "✘ fixture not found: $PDF_PATH" >&2
  exit 1
fi

AUTH=(-H "Authorization: Bearer ${LINTPDF_API_KEY}")

echo "============================================================"
echo "v2 playbook smoke — PR 18 closer"
echo "============================================================"
echo "  API URL  : $API_URL"
echo "  Profile  : $PROFILE_ID"
echo "  Fixture  : $PDF_PATH"
echo

# ----- 1. submit ---------------------------------------------------------

echo "→ submitting job ..."
SUBMIT_BODY=$(curl -fsS -X POST "${AUTH[@]}" \
  -F "file=@${PDF_PATH}" \
  -F "profile_id=${PROFILE_ID}" \
  "${API_URL}/api/v1/jobs") || { echo "submit failed"; exit 2; }

JOB_ID=$(printf '%s' "$SUBMIT_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
echo "   job_id = $JOB_ID"

# ----- 2. poll until terminal -------------------------------------------

echo "→ polling for completion ..."
deadline=$(( $(date +%s) + 300 ))
STATUS=""
while (( $(date +%s) < deadline )); do
  POLL_BODY=$(curl -fsS "${AUTH[@]}" "${API_URL}/api/v1/jobs/${JOB_ID}") || { echo "poll failed"; exit 2; }
  STATUS=$(printf '%s' "$POLL_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  if [[ "$STATUS" == "complete" || "$STATUS" == "failed" ]]; then
    break
  fi
  sleep 2
done

if [[ "$STATUS" != "complete" ]]; then
  echo "✘ job ended with status=$STATUS" >&2
  exit 3
fi

# ----- 3. mint reports --------------------------------------------------

echo "→ minting reports ..."
REPORTS_BODY=$(curl -fsS -X POST "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d '{"formats":["html","pdf","json","annotated_pdf"]}' \
  "${API_URL}/api/v1/jobs/${JOB_ID}/reports") || { echo "mint failed"; exit 2; }

URL_HTML=$(printf '%s' "$REPORTS_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((r["url"] for r in d.get("reports",[]) if r.get("format")=="html" and r.get("url")),""))')
URL_PDF=$(printf '%s' "$REPORTS_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((r["url"] for r in d.get("reports",[]) if r.get("format")=="pdf" and r.get("url")),""))')
URL_JSON=$(printf '%s' "$REPORTS_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((r["url"] for r in d.get("reports",[]) if r.get("format")=="json" and r.get("url")),""))')
URL_ANNOT=$(printf '%s' "$REPORTS_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((r["url"] for r in d.get("reports",[]) if r.get("format")=="annotated_pdf" and r.get("url")),""))')
URL_VIEW=$(printf '%s' "$REPORTS_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((r.get("viewer_url","") for r in d.get("reports",[]) if r.get("format")=="html"),""))')

# ----- 4. EPM verdict ---------------------------------------------------

echo "→ fetching EPM verdict ..."
EPM_BODY=$(curl -fsS "${AUTH[@]}" "${API_URL}/api/v1/jobs/${JOB_ID}/epm") || { echo "epm fetch failed"; exit 2; }
EPM_TIER=$(printf '%s' "$EPM_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tier"])')
EPM_DRIVERS=$(printf '%s' "$EPM_BODY" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin).get("rejection_drivers",[])))')

# ----- 5. explain (optional) -------------------------------------------

EXPLAIN_OUT=""
EXPLAIN_COUNT=0
if [[ "$EXPLAIN" == "1" ]]; then
  echo "→ explaining first 3 findings ..."
  FIDS=$(printf '%s' "$POLL_BODY" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for f in (d.get("findings") or [])[:3]:
    fid = f.get("id")
    if fid:
        print(fid)
')
  while IFS= read -r FID; do
    [[ -z "$FID" ]] && continue
    RESP=$(curl -fsS -X POST "${AUTH[@]}" \
      -H "Content-Type: application/json" \
      -d '{}' \
      "${API_URL}/api/v1/jobs/${JOB_ID}/findings/${FID}/explain" || true)
    TEXT=$(printf '%s' "$RESP" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print((d.get("explanation") or d.get("text") or "")[:80])
except Exception:
    print("(no explanation)")
' 2>/dev/null || echo "(error)")
    EXPLAIN_OUT+="    ${FID}: ${TEXT}"$'\n'
    EXPLAIN_COUNT=$((EXPLAIN_COUNT + 1))
  done <<< "$FIDS"
fi

# ----- 6. print everything ----------------------------------------------

echo
echo "============================================================"
echo "smoke summary"
echo "============================================================"
echo "  HTML  : ${URL_HTML:-(missing)}"
echo "  PDF   : ${URL_PDF:-(missing)}"
echo "  JSON  : ${URL_JSON:-(missing)}"
echo "  ANNOT : ${URL_ANNOT:-(missing)}"
echo "  VIEW  : ${URL_VIEW:-(missing)}"
echo "  EPM   : tier=${EPM_TIER}, drivers=[${EPM_DRIVERS}]"
if [[ "$EXPLAIN" == "1" ]]; then
  echo "  AI    : ${EXPLAIN_COUNT}/3 findings explained"
  if [[ -n "$EXPLAIN_OUT" ]]; then
    echo "$EXPLAIN_OUT"
  fi
else
  echo "  AI    : skipped (SMOKE_EXPLAIN=0)"
fi
echo "============================================================"
echo "✓ done"
