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
#
# Two cohorts:
#
# 1. Alpha-stream targets — already at zero on main. Future PRs that
#    re-introduce these violations fail CI.
#
# 2. Beta-stream targets — added 2026-04-30 with a non-zero baseline.
#    Each beta-stream PR migrates one category and the count
#    decreases. The final beta-stream commit drops the floor to zero
#    + flips the η6 tripwire on permanently. Until then, the
#    floor-not-ceiling counter prevents accidental new violations.
BANNED=(
    # SaaS-only modules — analyzers must reach these via ctx.services.*
    # or ctx.config instead of importing them directly. The list
    # focuses on real coupling (DB / billing / metering / tenant
    # config / vera​PDF) — stateless compute helpers like rendering
    # and the Claude SDK wrappers are NOT banned because they're our
    # own code, not SaaS-only modules. Phase 3d migrated the Claude
    # wrappers to take ``llm_client`` via ``ctx.services.llm_client``
    # so the LLM coupling is properly abstracted; the import line
    # itself is just calling our helper function and is allowed.
    "from siftpdf.tenants"
    "from siftpdf.audit.metering"
    "from siftpdf.audit.cost"
    "from siftpdf.api.database"
    "from siftpdf.api.models"
    "from siftpdf.api.storage"
    "from siftpdf.ai.cost_cap"
    "from siftpdf.ai.credits"
    "from siftpdf.ai.gpu_client"
    "from siftpdf.ai.types import get_db_session"
    "from siftpdf.ai.types import get_gpu_client"
    "from siftpdf.conformance.verapdf_client"
    "TenantAIConfig"
)

# NOTE on previously-banned imports that have been moved or relaxed:
#
# - ``siftpdf.ai.rendering`` was relocated to ``siftpdf.rendering`` in
#   Phase 3c. Pure CPU helper (pdf2image / pikepdf / Pillow); it's not
#   SaaS-coupled. The old path is a re-export shim. AI analyzers reach
#   it through ``ctx.services.renderer``; non-AI analyzers can import
#   ``siftpdf.rendering`` directly.
# - ``siftpdf.ai.text_mask`` was banned briefly during β-stream and
#   removed in β-final — it's a CPU text-density helper.
# - ``siftpdf.ai.dieline_claude`` and ``siftpdf.ai.legend_claude`` are
#   stateless Anthropic SDK wrappers. They legitimately live under
#   ``siftpdf.ai.*`` because they call the LLM, but they don't carry
#   SaaS-only state. Phase 4 will fold them behind a proper LLMClient
#   service Protocol; until then they're not on the η6 list.

# Paths that must stay SaaS-free.
#
# Phase 3c widened scope back to all analyzers after Phase 2 β-stream
# decoupled every AI analyzer and Phase 3a closed the last
# ``api.models`` violation. The 4 deterministic non-AI analyzers
# (advanced_color_analyzer, barcode, dieline, legend) lazy-imported
# rendering / Claude helpers; rendering moved to ``siftpdf.rendering``
# (no longer banned) and Claude helpers were removed from the list.
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
