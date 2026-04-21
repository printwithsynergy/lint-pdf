#!/usr/bin/env bash
# Run a preflight against the public LintPDF API and print the resulting
# report URLs. Supports the default tenant (LINTPDF_API_KEY from env) and
# the "pws" (Print With Synergy) demo tenant (credentials sourced from
# .lintpdf-demo-credentials.env produced by
# packages/engine/scripts/seed_pws_demo.py).
#
# Usage:
#   scripts/run-preflight.sh --tenant default                    # uses LINTPDF_API_KEY
#   scripts/run-preflight.sh --tenant pws                        # uses seed creds
#   scripts/run-preflight.sh --tenant default --file brochure.pdf
#   scripts/run-preflight.sh --tenant pws --profile-id lintpdf-default
#
# Env / file inputs:
#   LINTPDF_API_URL                 default https://api.lintpdf.com
#   LINTPDF_API_KEY                 required for --tenant default
#   .lintpdf-demo-credentials.env   required for --tenant pws (see seed_pws_demo.py)
#
# Exit codes:
#   0   job reached status=complete, report URLs printed
#   1   bad arguments or missing credentials
#   2   job failed
#   3   poll timed out
set -euo pipefail

TENANT=""
FILE=""
PROFILE_ID="lintpdf-default"
POLL_INTERVAL_S=2
POLL_TIMEOUT_S=180

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tenant) TENANT="${2:-}"; shift 2 ;;
    --file) FILE="${2:-}"; shift 2 ;;
    --profile-id) PROFILE_ID="${2:-}"; shift 2 ;;
    --poll-timeout) POLL_TIMEOUT_S="${2:-}"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown arg: $1" >&2; usage 1 ;;
  esac
done

if [[ -z "$TENANT" ]]; then
  echo "ERROR: --tenant is required (default | pws)" >&2
  usage 1
fi

# ---------------------------------------------------------------------------
# Resolve credentials + base URL
# ---------------------------------------------------------------------------
API_URL="${LINTPDF_API_URL:-https://api.lintpdf.com}"
case "$TENANT" in
  default)
    : "${LINTPDF_API_KEY:?LINTPDF_API_KEY must be set for --tenant default}"
    API_KEY="$LINTPDF_API_KEY"
    TENANT_LABEL="default"
    ;;
  pws)
    # seed_pws_demo.py writes creds next to this script, so resolve the
    # path relative to the script itself rather than CWD.
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CRED_FILE="$SCRIPT_DIR/.lintpdf-demo-credentials.env"
    if [[ ! -f "$CRED_FILE" ]]; then
      echo "ERROR: $CRED_FILE not found. Run:" >&2
      echo "  LINTPDF_ADMIN_KEY=... python3 packages/engine/scripts/seed_pws_demo.py" >&2
      exit 1
    fi
    # shellcheck disable=SC1090
    . "$CRED_FILE"
    : "${LINTPDF_DEMO_API_KEY:?LINTPDF_DEMO_API_KEY missing from $CRED_FILE}"
    API_KEY="$LINTPDF_DEMO_API_KEY"
    TENANT_LABEL="pws (Print With Synergy)"
    ;;
  *)
    echo "ERROR: unknown tenant '$TENANT' (default | pws)" >&2
    exit 1
    ;;
esac

# ---------------------------------------------------------------------------
# Resolve the file — fall back to a built-in minimal PDF if none supplied
# ---------------------------------------------------------------------------
if [[ -z "$FILE" ]]; then
  FILE="$(mktemp --suffix=.pdf)"
  # One-page, fully valid PDF 1.4. ~345 bytes, round-trips through every
  # parser we currently ship and is small enough to keep this script
  # self-contained — no fixture check-in required.
  cat >"$FILE" <<'PDF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
206
%%EOF
PDF
  GENERATED_FIXTURE=1
else
  if [[ ! -f "$FILE" ]]; then
    echo "ERROR: file not found: $FILE" >&2
    exit 1
  fi
  GENERATED_FIXTURE=0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required (brew install jq / apt-get install -y jq)" >&2
  exit 1
fi

echo "== LintPDF preflight =="
echo "tenant:       $TENANT_LABEL"
echo "api_url:      $API_URL"
echo "profile_id:   $PROFILE_ID"
echo "file:         $FILE ($(wc -c <"$FILE") bytes)"
echo

# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------
SUBMIT_RESP="$(curl -sS --fail-with-body \
  -X POST "$API_URL/api/v1/jobs" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@$FILE" \
  -F "profile_id=$PROFILE_ID")"

JOB_ID="$(jq -r '.job_id // empty' <<<"$SUBMIT_RESP")"
if [[ -z "$JOB_ID" ]]; then
  echo "ERROR: no job_id in submit response:" >&2
  echo "$SUBMIT_RESP" >&2
  exit 2
fi
echo "submitted: job_id=$JOB_ID"

# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------
DEADLINE=$(( $(date +%s) + POLL_TIMEOUT_S ))
STATUS=""
JOB_JSON=""

while (( $(date +%s) < DEADLINE )); do
  JOB_JSON="$(curl -sS --fail-with-body \
    -H "Authorization: Bearer $API_KEY" \
    "$API_URL/api/v1/jobs/$JOB_ID")"
  STATUS="$(jq -r '.status' <<<"$JOB_JSON")"
  printf "  status=%-12s" "$STATUS"
  case "$STATUS" in
    complete|completed) echo "✓"; break ;;
    failed) echo "✗"; break ;;
    *) echo "…"; sleep "$POLL_INTERVAL_S" ;;
  esac
done

if [[ -z "$STATUS" ]]; then
  echo "ERROR: never received job status within ${POLL_TIMEOUT_S}s" >&2
  exit 3
fi

if [[ "$STATUS" == "failed" ]]; then
  echo "ERROR: job failed:" >&2
  jq '.error_message // .' <<<"$JOB_JSON" >&2
  exit 2
fi

if [[ "$STATUS" != "complete" && "$STATUS" != "completed" ]]; then
  echo "ERROR: poll timed out at status=$STATUS" >&2
  exit 3
fi

# ---------------------------------------------------------------------------
# Generate + print report URLs
#
# ``reports`` on the GET response is populated only when ReportToken rows
# already exist for the job. Until a caller explicitly requests formats via
# ``POST /api/v1/jobs/{id}/reports`` there's nothing to mint URLs from, so
# fetch-then-print on GET alone always returns null. We POST to generate,
# then list so we always print something actionable.
# ---------------------------------------------------------------------------
echo
echo "== Generating hosted report tokens (pdf + html + json) =="
GEN_RESP="$(curl -sS --fail-with-body \
  -X POST "$API_URL/api/v1/jobs/$JOB_ID/reports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"formats": ["pdf", "html", "json"]}')"

if jq -e '.reports // .tokens // empty' <<<"$GEN_RESP" >/dev/null; then
  jq -r '
    (.reports // .tokens) |
    (if type == "object" then to_entries else . end) |
    .[] |
    "  \(.key // .format):\t\(.value // .url)"
  ' <<<"$GEN_RESP"
else
  echo "  (report generation response did not include reports; raw output below)"
  jq . <<<"$GEN_RESP"
fi

if (( GENERATED_FIXTURE == 1 )); then
  rm -f "$FILE"
fi
