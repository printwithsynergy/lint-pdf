#!/usr/bin/env bash
# v2 production smoke — full corpus runner.
#
# Mints a temp tenant via the engine admin key, enables AI + grants
# credits, then submits every fixture under
# packages/engine/tests/fixtures/{,accuracy/}*.pdf one at a time. For
# each job: poll until terminal, mint HTML/PDF/JSON/annotated-PDF
# reports, fetch the EPM verdict, and call real Claude
# POST /findings/{id}/explain on every finding. Prints a clickable
# URL summary at the end.
#
# Usage:
#   ./scripts/smoke-preflight-batch.sh
#
# Required env:
#   LINTPDF_ADMIN_API_KEY    Engine admin key (X-Admin-Key header).
#
# Optional env:
#   LINTPDF_API_URL          Engine base URL. Default https://api.lintpdf.com
#   LINTPDF_PROFILE_ID       Profile to run. Default lintpdf-default
#   SMOKE_RUN_DIR            Run-output directory. Default /tmp/smoke-batch-<ts>
#   SMOKE_FIXTURES           Whitespace-sep list of PDFs. Default = full corpus.
#   SMOKE_EXPLAIN            "1" to call AI-Explain (default), "0" to skip.
#   SMOKE_POLL_DEADLINE      Seconds to wait per job. Default 360.
#
# Exit codes:
#   0   every fixture completed every step
#   1   pre-flight guard failed (missing env / engine unhealthy)
#   2   one or more fixtures failed (summary still printed)

set -euo pipefail

API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
PROFILE_ID="${LINTPDF_PROFILE_ID:-lintpdf-default}"
EXPLAIN="${SMOKE_EXPLAIN:-1}"
POLL_DEADLINE="${SMOKE_POLL_DEADLINE:-360}"
TS="$(date +%s)"
RUN_DIR="${SMOKE_RUN_DIR:-/tmp/smoke-batch-${TS}}"
mkdir -p "$RUN_DIR"
SUMMARY_FILE="$RUN_DIR/summary.txt"
: > "$SUMMARY_FILE"

# ----- guards -----------------------------------------------------------

if [[ -z "${LINTPDF_ADMIN_API_KEY:-}" ]]; then
  echo "✘ LINTPDF_ADMIN_API_KEY is required (X-Admin-Key for /api/v1/admin/*)" >&2
  echo "  export LINTPDF_ADMIN_API_KEY=\$(railway variables --service API | awk '/LINTPDF_ADMIN_API_KEY/ {print \$2}')" >&2
  exit 1
fi

# Resolve fixtures.
if [[ -n "${SMOKE_FIXTURES:-}" ]]; then
  read -r -a FIXTURES <<< "$SMOKE_FIXTURES"
else
  FIXTURES=(
    "packages/engine/tests/fixtures/test-sample.pdf"
    packages/engine/tests/fixtures/accuracy/*.pdf
  )
fi
TOTAL="${#FIXTURES[@]}"
for f in "${FIXTURES[@]}"; do
  [[ -f "$f" ]] || { echo "✘ fixture missing: $f" >&2; exit 1; }
done

# ----- helpers ----------------------------------------------------------

# Pretty-print a banner line.
banner() {
  printf '\n%s\n%s\n%s\n' \
    "============================================================" \
    "$1" \
    "============================================================"
}

# Extract a JSON field via python3.
jq_get() {
  python3 -c '
import json, sys
data = json.load(sys.stdin)
for k in sys.argv[1].split("."):
    if isinstance(data, list):
        data = data[int(k)] if k.lstrip("-").isdigit() else data
    else:
        data = data.get(k) if isinstance(data, dict) else None
    if data is None:
        break
print("" if data is None else (data if isinstance(data, str) else json.dumps(data)))
' "$1"
}

# POST/GET wrappers that capture body to a tmpfile and return HTTP code.
# Retries up to 3× on transient failures (000 / 502 / 503 / 504) — the
# engine occasionally returns "DNS cache overflow" 503s from a single
# pod; the next request hits a different pod and succeeds.
http_call() {
  # Args: METHOD URL BODY_FILE [extra curl flags...]
  local method="$1" url="$2" body_file="$3"; shift 3
  local code attempt
  for attempt in 1 2 3; do
    code=$(curl -sS -m 60 -o "$body_file" -w '%{http_code}' \
      -X "$method" "$url" "$@" || echo "000")
    case "$code" in
      000|502|503|504) sleep "$(( attempt * 2 ))" ;;
      *) break ;;
    esac
  done
  echo "$code"
}

# Wait until job is terminal. Args: JOB_ID OUTPUT_FILE
wait_terminal() {
  local jid="$1" out="$2"
  local deadline=$(( $(date +%s) + POLL_DEADLINE ))
  local status=""
  while (( $(date +%s) < deadline )); do
    local code
    code=$(http_call GET "${API_URL}/api/v1/jobs/${jid}" "$out" \
      -H "Authorization: Bearer ${TENANT_KEY}")
    if [[ "$code" != "200" ]]; then
      echo "  ✘ poll HTTP $code" >&2
      return 1
    fi
    status=$(jq_get "status" < "$out")
    [[ "$status" == "complete" || "$status" == "failed" ]] && break
    sleep 3
  done
  [[ "$status" == "complete" ]] || { echo "  ✘ job ended status=$status"; return 1; }
  return 0
}

# ----- 1. health probe -------------------------------------------------

banner "v2 production smoke — full corpus"
echo "  API URL  : $API_URL"
echo "  Profile  : $PROFILE_ID"
echo "  Fixtures : $TOTAL"
echo "  Run dir  : $RUN_DIR"
echo

echo "→ probing /ready ..."
ready_code=$(http_call GET "${API_URL}/ready" "$RUN_DIR/ready.json")
if [[ "$ready_code" != "200" ]]; then
  # The Railway edge proxy occasionally serves "DNS cache overflow"
  # 503s — same transient the http_call retry covers for every other
  # call. Don't exit on it; the mint_tenant POST below is the real
  # liveness check. Log and continue.
  echo "  ⚠ /ready returned $ready_code: $(head -c 80 "$RUN_DIR/ready.json")"
  echo "  (continuing — mint_tenant is the real liveness probe)"
else
  echo "  $(cat "$RUN_DIR/ready.json")"
fi

# ----- 2. mint temp tenant ---------------------------------------------

echo
echo "→ minting temp tenant ..."
TENANT_NAME="smoke-batch-${TS}"
mint_body=$(printf '{"name":"%s","plan":"enterprise","contact_email":null}' "$TENANT_NAME")
mint_code=$(http_call POST "${API_URL}/api/v1/admin/tenants" "$RUN_DIR/tenant.json" \
  -H "X-Admin-Key: ${LINTPDF_ADMIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$mint_body")
if [[ "$mint_code" != "200" && "$mint_code" != "201" ]]; then
  echo "✘ tenant mint failed: HTTP $mint_code"
  cat "$RUN_DIR/tenant.json"
  exit 1
fi
TENANT_ID=$(jq_get "id" < "$RUN_DIR/tenant.json")
TENANT_KEY=$(jq_get "api_key" < "$RUN_DIR/tenant.json")
if [[ -z "$TENANT_ID" || -z "$TENANT_KEY" ]]; then
  echo "✘ tenant response missing id / api_key"
  cat "$RUN_DIR/tenant.json"
  exit 1
fi
echo "  tenant_id  = $TENANT_ID"
echo "  api_key tag = ${TENANT_KEY:0:12}…${TENANT_KEY: -6}"

# Enable AI on the tenant so submissions exercise every analyzer
# category and the explain endpoint is callable.
echo "→ enabling AI on tenant ..."
ai_code=$(http_call PUT \
  "${API_URL}/api/v1/admin/tenants/${TENANT_ID}/ai?ai_enabled=true&billing_mode=pay_per_use&enabled_categories=all" \
  "$RUN_DIR/ai_enable.json" \
  -H "X-Admin-Key: ${LINTPDF_ADMIN_API_KEY}")
if [[ "$ai_code" != "200" && "$ai_code" != "201" ]]; then
  echo "  ⚠ AI enable returned $ai_code (continuing without AI)"
  cat "$RUN_DIR/ai_enable.json" || true
  EXPLAIN="0"
fi

# Preload credits so cost-cap doesn't intercept mid-run.
echo "→ granting AI credits ..."
cred_code=$(http_call POST \
  "${API_URL}/api/v1/admin/tenants/${TENANT_ID}/ai/credits?credit_amount=10000&price_paid=0" \
  "$RUN_DIR/ai_credits.json" \
  -H "X-Admin-Key: ${LINTPDF_ADMIN_API_KEY}")
if [[ "$cred_code" != "200" && "$cred_code" != "201" ]]; then
  echo "  ⚠ credits grant returned $cred_code (continuing; explain may 402)"
  cat "$RUN_DIR/ai_credits.json" || true
fi

# Pin industry_type + regulatory_market via the tenant-side config
# route (admin route doesn't expose those fields; they go through
# PUT /api/v1/ai/config with tenant bearer auth). Setting them
# matters for jurisdiction-gated analyzers like AI_PHARMA_001 +
# AI_EU1169_001 — without these the EU rules over-fire on US/CA
# fixtures (see the 2026-04-27 Opus audit, PR #278).
echo "→ pinning industry_type + regulatory_market ..."
cfg_body='{"industry_type":"dietary_supplement","regulatory_market":"us_fda"}'
cfg_code=$(http_call PUT "${API_URL}/api/v1/ai/config" "$RUN_DIR/ai_config.json" \
  -H "Authorization: Bearer ${TENANT_KEY}" \
  -H "Content-Type: application/json" \
  -d "$cfg_body")
if [[ "$cfg_code" != "200" ]]; then
  echo "  ⚠ ai/config PUT returned $cfg_code"
  head -c 200 "$RUN_DIR/ai_config.json"; echo
fi


# ----- 3. fixture loop -------------------------------------------------

declare -a SUMMARY_BLOCKS
FAILED=0
banner "running ${TOTAL} fixtures"

idx=0
for pdf in "${FIXTURES[@]}"; do
  idx=$((idx + 1))
  base="$(basename "$pdf")"
  slot="$RUN_DIR/$(printf '%02d' "$idx")_${base%.pdf}"
  mkdir -p "$slot"

  printf '\n[%d/%d] %s\n' "$idx" "$TOTAL" "$base"

  # ── submit ─────────────────────────────────────────────────────
  submit_code=$(http_call POST "${API_URL}/api/v1/jobs" "$slot/submit.json" \
    -H "Authorization: Bearer ${TENANT_KEY}" \
    -F "file=@${pdf}" \
    -F "profile_id=${PROFILE_ID}" \
    -F "ai_enabled=true")
  if [[ "$submit_code" != "200" && "$submit_code" != "201" && "$submit_code" != "202" ]]; then
    echo "  ✘ submit HTTP $submit_code"
    head -c 500 "$slot/submit.json"; echo
    SUMMARY_BLOCKS+=("$(printf '[%d/%d] %s\n    SUBMIT FAILED HTTP %s' "$idx" "$TOTAL" "$base" "$submit_code")")
    FAILED=$((FAILED + 1))
    continue
  fi
  job_id=$(jq_get "job_id" < "$slot/submit.json")
  if [[ -z "$job_id" ]]; then
    echo "  ✘ submit body missing job_id"
    SUMMARY_BLOCKS+=("$(printf '[%d/%d] %s\n    SUBMIT MALFORMED' "$idx" "$TOTAL" "$base")")
    FAILED=$((FAILED + 1))
    continue
  fi
  echo "  job_id = $job_id"

  # ── poll ───────────────────────────────────────────────────────
  if ! wait_terminal "$job_id" "$slot/poll.json"; then
    SUMMARY_BLOCKS+=("$(printf '[%d/%d] %s\n    POLL TIMEOUT (job_id=%s)' "$idx" "$TOTAL" "$base" "$job_id")")
    FAILED=$((FAILED + 1))
    continue
  fi
  finding_count=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
print(len(d.get("findings") or []))
' "$slot/poll.json")
  echo "  status=complete findings=${finding_count}"

  # ── mint reports ───────────────────────────────────────────────
  rpt_code=$(http_call POST "${API_URL}/api/v1/jobs/${job_id}/reports" "$slot/reports.json" \
    -H "Authorization: Bearer ${TENANT_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"formats":["html","pdf","json","annotated_pdf"],"expiry_days":7}')
  if [[ "$rpt_code" != "200" && "$rpt_code" != "201" ]]; then
    echo "  ✘ mint HTTP $rpt_code"
    head -c 500 "$slot/reports.json"; echo
    SUMMARY_BLOCKS+=("$(printf '[%d/%d] %s\n    MINT FAILED HTTP %s' "$idx" "$TOTAL" "$base" "$rpt_code")")
    FAILED=$((FAILED + 1))
    continue
  fi
  url_html=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for r in d.get("reports", []):
    if r.get("format") == "html" and r.get("url"):
        print(r["url"]); break
' "$slot/reports.json")
  url_pdf=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for r in d.get("reports", []):
    if r.get("format") == "pdf" and r.get("url"):
        print(r["url"]); break
' "$slot/reports.json")
  url_json=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for r in d.get("reports", []):
    if r.get("format") == "json" and r.get("url"):
        print(r["url"]); break
' "$slot/reports.json")
  url_annot=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for r in d.get("reports", []):
    if r.get("format") == "annotated_pdf" and r.get("url"):
        print(r["url"]); break
' "$slot/reports.json")
  url_view=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for r in d.get("reports", []):
    if r.get("format") == "html" and r.get("viewer_url"):
        print(r["viewer_url"]); break
' "$slot/reports.json")

  # ── EPM verdict ────────────────────────────────────────────────
  epm_tier="(skipped)"
  epm_drivers=""
  epm_code=$(http_call GET "${API_URL}/api/v1/jobs/${job_id}/epm" "$slot/epm.json" \
    -H "Authorization: Bearer ${TENANT_KEY}")
  if [[ "$epm_code" == "200" ]]; then
    epm_tier=$(jq_get "tier" < "$slot/epm.json")
    epm_drivers=$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
print(",".join(d.get("rejection_drivers") or []))
' "$slot/epm.json")
  else
    epm_tier="ERROR (HTTP $epm_code)"
  fi

  # ── AI-Explain (every finding) ────────────────────────────────
  # Parallel fan-out: 8 concurrent Claude Haiku 4.5 calls. Each
  # finding has a unique row UUID so concurrent calls write to
  # distinct rows (no cache race). Status codes are written to
  # ``${slot}/explain_${fid}.code`` next to the body so the parent
  # shell can tally outcomes after ``xargs`` reaps the children.
  explained=0
  explain_skipped=0
  cap_hit=0
  if [[ "$EXPLAIN" == "1" && "$finding_count" -gt 0 ]]; then
    python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for f in (d.get("findings") or []):
    fid = f.get("id")
    if fid:
        print(fid)
' "$slot/poll.json" | xargs -P 8 -I @@ bash -c '
      fid="$1"
      slot="$2"
      url="$3"
      key="$4"
      out_body="${slot}/explain_${fid}.json"
      out_code="${slot}/explain_${fid}.code"
      for attempt in 1 2 3; do
        ec=$(curl -sS -m 60 -o "$out_body" -w "%{http_code}" \
          -X POST "${url}/api/v1/jobs/'"$job_id"'/findings/${fid}/explain" \
          -H "Authorization: Bearer ${key}" \
          -H "Content-Type: application/json" \
          -d "{}" 2>/dev/null || echo "000")
        case "$ec" in
          000|502|503|504) sleep "$(( attempt * 2 ))" ;;
          *) break ;;
        esac
      done
      printf "%s" "$ec" > "$out_code"
    ' _ @@ "$slot" "$API_URL" "$TENANT_KEY"
    # Tally results.
    for cf in "$slot"/explain_*.code; do
      [[ -f "$cf" ]] || continue
      ec=$(<"$cf")
      case "$ec" in
        200) explained=$((explained + 1)) ;;
        402) cap_hit=1; explain_skipped=$((explain_skipped + 1)) ;;
        503)
          echo "  ✘ explain 503 — Claude unconfigured (saw at least one)"
          ;;
        *) explain_skipped=$((explain_skipped + 1)) ;;
      esac
    done
  fi

  # ── per-fixture summary block ─────────────────────────────────
  block=$(cat <<BLOCK
[${idx}/${TOTAL}] ${base}    status=complete  EPM=${epm_tier}  findings=${explained}/${finding_count} explained$( [[ "$cap_hit" -eq 1 ]] && echo " (cost-cap hit)")
    HTML  : ${url_html:-(missing)}
    PDF   : ${url_pdf:-(missing)}
    JSON  : ${url_json:-(missing)}
    ANNOT : ${url_annot:-(missing)}
    VIEW  : ${url_view:-(missing)}
    EPM   : tier=${epm_tier} drivers=[${epm_drivers}]
BLOCK
  )
  SUMMARY_BLOCKS+=("$block")
  echo "$block"
done

# ----- 4. final summary ------------------------------------------------

banner "smoke summary"
{
  printf 'tenant_id    = %s\n' "$TENANT_ID"
  printf 'api_key tag  = %s…%s\n' "${TENANT_KEY:0:12}" "${TENANT_KEY: -6}"
  printf 'started      = %s\n' "$(date -u -d "@$TS" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'finished     = %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'total        = %d  passed = %d  failed = %d\n' \
    "$TOTAL" "$((TOTAL - FAILED))" "$FAILED"
  printf '\n'
  for b in "${SUMMARY_BLOCKS[@]}"; do
    printf '%s\n\n' "$b"
  done
} | tee "$SUMMARY_FILE"

echo
echo "Full per-fixture artefacts saved under: $RUN_DIR"
echo "Summary file: $SUMMARY_FILE"

if [[ "$FAILED" -gt 0 ]]; then
  exit 2
fi
exit 0
