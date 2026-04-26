"""Q-C7 — 16 LPDF_EPM_*_REJECT inspection IDs covering the EPM-A/B/C
v2-universe checks not already present in the legacy
``LPDF_EPM_001..018`` set.

Each constant maps to exactly one v2 ID. Friendly names and
descriptions live in :mod:`lintpdf.reports.check_names`; the
inspection IDs here are the source of truth for analyzer modules
that emit the findings.

Tier semantics (per playbook §2.EPM):

* **A — reject**: any A-tier finding rejects the job from EPM.
* **B — soft reject**: B-tier findings each individually nudge the
  scorer toward "marginal"; >=2 B-tier findings reject.
* **C — advisory**: C-tier findings inform the operator without
  changing the scorer's verdict.
"""

from __future__ import annotations

# ── Tier A: hard rejections ────────────────────────────────────────────

# EPM-A1: out-of-gamut spot colors / Lab values that CMY can't reach
EPM_GAMUT_OUT_OF_REACH = "LPDF_EPM_GAMUT_OUT_REJECT"
# EPM-A2: K-channel coverage above tolerance — too much K to drop cleanly
EPM_K_COVERAGE_TOO_HIGH = "LPDF_EPM_K_COVERAGE_REJECT"
# EPM-A3: rich-black recipe deviates from configured default
EPM_RICH_BLACK_DEVIATION = "LPDF_EPM_RICH_BLACK_REJECT"
# EPM-A6: substrate class incompatible with EPM (e.g. uncoated heavy stock)
EPM_SUBSTRATE_INCOMPATIBLE = "LPDF_EPM_SUBSTRATE_REJECT"
# EPM-A8: minimum non-black text point size below threshold (CMY-only loss
# of contrast on tiny text)
EPM_TEXT_TOO_SMALL_FOR_CMY = "LPDF_EPM_TEXT_SIZE_REJECT"

# ── Tier B: soft rejections ────────────────────────────────────────────

# EPM-B1: process color count exceeds 4 (additional plates blow throughput
# advantage)
EPM_PROCESS_COLOR_COUNT = "LPDF_EPM_PROCESS_COUNT_REJECT"
# EPM-B3: insufficient bleed for digital trim (press-side waste)
EPM_BLEED_BELOW_MIN = "LPDF_EPM_BLEED_REJECT"
# EPM-B4: page count below the economic break-even for an EPM run
EPM_PAGE_COUNT_BELOW_ECONOMIC = "LPDF_EPM_PAGE_COUNT_REJECT"
# EPM-B5: image resolution below digital-press minimum (artifact risk)
EPM_IMAGE_RES_BELOW_DIGITAL = "LPDF_EPM_IMAGE_RES_REJECT"
# EPM-B6: trim/bleed boxes inconsistent across pages (finishing risk)
EPM_TRIM_INCONSISTENT = "LPDF_EPM_TRIM_REJECT"

# ── Tier C: advisory ───────────────────────────────────────────────────

# EPM-C1: spot color count above advisory cap — may indicate a non-EPM
# workflow was assumed
EPM_SPOT_COUNT_HIGH = "LPDF_EPM_SPOT_COUNT_REJECT"
# EPM-C2: smallest stroked feature below digital-press resolution
EPM_FEATURE_BELOW_DIGITAL_RES = "LPDF_EPM_FEATURE_SIZE_REJECT"
# EPM-C3: mixed process color spaces in same job (some pages CMYK, some
# DeviceN) — warns operators to confirm setup
EPM_MIXED_PROCESS_SPACES = "LPDF_EPM_MIXED_SPACES_REJECT"
# EPM-C5: trapping settings disabled (digital presses still benefit from
# explicit traps on tight register)
EPM_TRAPPING_DISABLED = "LPDF_EPM_TRAPPING_REJECT"
# EPM-C6: trim and bleed boxes mis-aligned (visible at finishing)
EPM_TRIM_BLEED_MISALIGNED = "LPDF_EPM_TRIM_BLEED_REJECT"
# EPM-C7: per-page geometry varies (some pages bleed correctly, others
# don't) — operator pulse before scheduling
EPM_PAGE_GEOMETRY_VARIES = "LPDF_EPM_PAGE_GEOM_REJECT"


# Convenience tuples for analyzer / scoring code that wants to walk
# the tier without hard-coding the v2 ID grouping.

TIER_A_CODES: tuple[str, ...] = (
    EPM_GAMUT_OUT_OF_REACH,
    EPM_K_COVERAGE_TOO_HIGH,
    EPM_RICH_BLACK_DEVIATION,
    EPM_SUBSTRATE_INCOMPATIBLE,
    EPM_TEXT_TOO_SMALL_FOR_CMY,
)

TIER_B_CODES: tuple[str, ...] = (
    EPM_PROCESS_COLOR_COUNT,
    EPM_BLEED_BELOW_MIN,
    EPM_PAGE_COUNT_BELOW_ECONOMIC,
    EPM_IMAGE_RES_BELOW_DIGITAL,
    EPM_TRIM_INCONSISTENT,
)

TIER_C_CODES: tuple[str, ...] = (
    EPM_SPOT_COUNT_HIGH,
    EPM_FEATURE_BELOW_DIGITAL_RES,
    EPM_MIXED_PROCESS_SPACES,
    EPM_TRAPPING_DISABLED,
    EPM_TRIM_BLEED_MISALIGNED,
    EPM_PAGE_GEOMETRY_VARIES,
)


# Map each new code → its v2 ID for fast lookups in the scorer + tests.
V2_ID_BY_CODE: dict[str, str] = {
    EPM_GAMUT_OUT_OF_REACH: "EPM-A1",
    EPM_K_COVERAGE_TOO_HIGH: "EPM-A2",
    EPM_RICH_BLACK_DEVIATION: "EPM-A3",
    EPM_SUBSTRATE_INCOMPATIBLE: "EPM-A6",
    EPM_TEXT_TOO_SMALL_FOR_CMY: "EPM-A8",
    EPM_PROCESS_COLOR_COUNT: "EPM-B1",
    EPM_BLEED_BELOW_MIN: "EPM-B3",
    EPM_PAGE_COUNT_BELOW_ECONOMIC: "EPM-B4",
    EPM_IMAGE_RES_BELOW_DIGITAL: "EPM-B5",
    EPM_TRIM_INCONSISTENT: "EPM-B6",
    EPM_SPOT_COUNT_HIGH: "EPM-C1",
    EPM_FEATURE_BELOW_DIGITAL_RES: "EPM-C2",
    EPM_MIXED_PROCESS_SPACES: "EPM-C3",
    EPM_TRAPPING_DISABLED: "EPM-C5",
    EPM_TRIM_BLEED_MISALIGNED: "EPM-C6",
    EPM_PAGE_GEOMETRY_VARIES: "EPM-C7",
}


__all__ = [
    "EPM_BLEED_BELOW_MIN",
    "EPM_FEATURE_BELOW_DIGITAL_RES",
    "EPM_GAMUT_OUT_OF_REACH",
    "EPM_IMAGE_RES_BELOW_DIGITAL",
    "EPM_K_COVERAGE_TOO_HIGH",
    "EPM_MIXED_PROCESS_SPACES",
    "EPM_PAGE_COUNT_BELOW_ECONOMIC",
    "EPM_PAGE_GEOMETRY_VARIES",
    "EPM_PROCESS_COLOR_COUNT",
    "EPM_RICH_BLACK_DEVIATION",
    "EPM_SPOT_COUNT_HIGH",
    "EPM_SUBSTRATE_INCOMPATIBLE",
    "EPM_TEXT_TOO_SMALL_FOR_CMY",
    "EPM_TRAPPING_DISABLED",
    "EPM_TRIM_BLEED_MISALIGNED",
    "EPM_TRIM_INCONSISTENT",
    "TIER_A_CODES",
    "TIER_B_CODES",
    "TIER_C_CODES",
    "V2_ID_BY_CODE",
]
