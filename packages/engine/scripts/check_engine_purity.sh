#!/usr/bin/env bash
# check_engine_purity.sh — Phase 1 / Track A guard.
#
# Fails CI if an analyzer path imports a SaaS-only module directly.
# Plugin migration (Phase 2) will turn each violation into a use of
# ``ctx.services.*`` or ``ctx.config["ai_config"]`` instead.
#
# Run this from the engine package root:
#     bash scripts/check_engine_purity.sh
#
# It scans ONLY the analyzer paths. SaaS modules are free to import
# each other; the rule is one-directional (analyzers must not depend
# on SaaS).
#
# Today this runs as a tripwire — Phase 1 leaves the existing
# violations in place (the host bridge + analyze_v2 default impl
# preserves behaviour) and uses a baseline counter so accidental
# *new* violations fail the build. The baseline file lives at
# ``scripts/engine_purity_baseline.txt`` and is regenerated whenever
# Phase 2 lands an analyzer migration.

set -euo pipefail

cd "$(dirname "$0")/.."

# Banned SaaS modules — analyzers must reach these via ctx.services.*
# or ctx.config instead of a direct import.
BANNED=(
    "from lintpdf.tenants"
    "from lintpdf.audit.metering"
    "from lintpdf.audit.cost"
    "from lintpdf.api.database"
    "from lintpdf.ai.cost_cap"
    "from lintpdf.ai.credits"
    "from lintpdf.ai.gpu_client"
    "from lintpdf.conformance.verapdf_client"
    "TenantAIConfig"
)

# Paths that must stay SaaS-free.
SCOPES=(
    "src/lintpdf/analyzers"
    "src/lintpdf/ai/analyzers"
)

BASELINE_FILE="scripts/engine_purity_baseline.txt"
TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

for scope in "${SCOPES[@]}"; do
    [ -d "$scope" ] || continue
    for pattern in "${BANNED[@]}"; do
        # -F: fixed string. -r: recursive. -n: line numbers. -l: omit.
        # We want one line per match (path + line), suitable for diffing
        # against the baseline.
        grep -rn -F "$pattern" "$scope" 2>/dev/null \
            | awk -F: -v pat="$pattern" '{print $1 ":" $2 ":" pat}' \
            >> "$TMP_OUT" || true
    done
done

CURRENT_COUNT="$(wc -l < "$TMP_OUT" | tr -d ' ')"

if [ ! -f "$BASELINE_FILE" ]; then
    # First run on a fresh checkout — establish the baseline.
    sort -u "$TMP_OUT" > "$BASELINE_FILE"
    echo "engine-purity: established baseline at $BASELINE_FILE ($CURRENT_COUNT entries)"
    exit 0
fi

BASELINE_COUNT="$(wc -l < "$BASELINE_FILE" | tr -d ' ')"

if [ "$CURRENT_COUNT" -gt "$BASELINE_COUNT" ]; then
    echo "❌ engine-purity: $CURRENT_COUNT violations (baseline: $BASELINE_COUNT)"
    echo
    echo "New SaaS imports detected inside analyzer paths. Use"
    echo "ctx.services.* or ctx.config[\"ai_config\"] instead of:"
    echo
    diff <(sort -u "$BASELINE_FILE") <(sort -u "$TMP_OUT") \
        | grep '^>' | sed 's/^> /  /' || true
    echo
    echo "If you intentionally migrated an analyzer (deleted a SaaS"
    echo "import — count went DOWN), regenerate the baseline:"
    echo "    sort -u "'<(scripts/check_engine_purity.sh 2>/dev/null)'" > $BASELINE_FILE"
    exit 1
fi

if [ "$CURRENT_COUNT" -lt "$BASELINE_COUNT" ]; then
    echo "✓ engine-purity: $CURRENT_COUNT violations (baseline: $BASELINE_COUNT — DOWN $((BASELINE_COUNT - CURRENT_COUNT)))"
    echo "  Regenerate the baseline to lock in the improvement:"
    echo "    cat $TMP_OUT | sort -u > $BASELINE_FILE"
    # Don't fail the build on improvement — just nudge.
    exit 0
fi

echo "✓ engine-purity: $CURRENT_COUNT violations (matches baseline)"
