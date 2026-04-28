"""Q-C2 / Q-C3 / Q-C7 — deterministic EPM candidacy scorer.

Walks the list of fired EPM-tier findings (legacy ``LPDF_EPM_001..018``
plus the new ``LPDF_EPM_*_REJECT`` codes from :mod:`lintpdf.epm.codes`)
and produces a verdict the routing dashboard can act on without
asking an operator to interpret raw findings.

Decision tree (mirrors the playbook §2.EPM):

* **Reject** — any A-tier finding fires, OR ≥ 2 B-tier findings fire.
  The job is unsuitable for EPM; route to standard CMYK.
* **Marginal** — exactly 1 B-tier finding fires (no A-tier). The
  operator decides: either remediate the B-tier or accept a known
  trade-off.
* **Pass-with-advisory** — 0 A-tier + 0 B-tier + ≥ 1 C-tier. EPM is
  recommended; advisories surface for context.
* **Pass** — no EPM findings fired at all.

Q-C6 IndiChrome upsell hint: when the verdict is **Reject** AND the
rejection drivers are spot-color-related (out-of-gamut, spot-count,
spot-fidelity), the result includes ``recommends_indichrome=True``
so the dashboard can prompt the operator to consider the IndiChrome
expanded-gamut workflow as a recovery path.

The scorer is pure: no DB, no I/O, deterministic for a given input.
Callers (analyzers / API responses / dashboard summary) hand in the
list of fired inspection ids; the scorer returns a structured
:class:`EpmVerdict`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from lintpdf.epm.codes import (
    EPM_GAMUT_OUT_OF_REACH,
    EPM_SPOT_COUNT_HIGH,
    TIER_A_CODES,
    TIER_B_CODES,
    TIER_C_CODES,
)


class EpmTier(StrEnum):
    """Verdict ranks. Pass < PassWithAdvisory < Marginal < Reject."""

    PASS = "pass"
    PASS_WITH_ADVISORY = "pass_with_advisory"
    MARGINAL = "marginal"
    REJECT = "reject"


@dataclass(frozen=True)
class EpmVerdict:
    """Structured result the routing dashboard renders.

    ``rejection_drivers`` lists the inspection ids that pushed the
    verdict to its tier (A-tier ids when REJECT-by-A, B-tier ids when
    REJECT-by-2B or MARGINAL). ``advisories`` lists the C-tier ids.
    ``recommends_indichrome`` is set per Q-C6 when the rejection
    reason is spot-color-related and a wider-gamut alternative would
    likely recover the job.
    """

    tier: EpmTier
    rejection_drivers: tuple[str, ...] = ()
    advisories: tuple[str, ...] = ()
    recommends_indichrome: bool = False
    legacy_codes_fired: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passes(self) -> bool:
        return self.tier in (EpmTier.PASS, EpmTier.PASS_WITH_ADVISORY)


# Legacy LPDF_EPM_001..018 codes that the scorer still needs to weigh.
# Each one was decided in the original Phase-2.EPM design pass; tier
# membership here keeps the scorer truthful even when an analyzer
# emits a legacy code instead of one of the new ``_REJECT`` codes.
_LEGACY_TIER_A: frozenset[str] = frozenset(
    {
        # Hard EPM rejections from the legacy set
        "LPDF_EPM_001",  # K-channel usage anywhere
        "LPDF_EPM_002",  # pure-K text
        "LPDF_EPM_006",  # image K-channel dependency
        "LPDF_EPM_007",  # registration colour
    }
)
_LEGACY_TIER_B: frozenset[str] = frozenset(
    {
        "LPDF_EPM_003",  # weak CMY composite
        "LPDF_EPM_004",  # CMY TAC over threshold
        "LPDF_EPM_005",  # spot K-dependent fallback
        "LPDF_EPM_008",  # gray balance risk
        "LPDF_EPM_009",  # toner limit exceeded
        "LPDF_EPM_018",  # thin stroke under digital min
    }
)
_LEGACY_TIER_C: frozenset[str] = frozenset(
    {
        "LPDF_EPM_010",  # per-channel ink limit
        "LPDF_EPM_011",  # spot fidelity risk
        "LPDF_EPM_012",  # variable-data indicators
        "LPDF_EPM_013",  # custom halftone in ExtGState
        "LPDF_EPM_014",  # output intent profile-class mismatch
        "LPDF_EPM_015",  # white-ink underlayer
        "LPDF_EPM_016",  # overprint simulation mode
        "LPDF_EPM_017",  # high object count
    }
)

# Codes that, when present in the rejection drivers, make the
# IndiChrome upsell relevant (Q-C6).
_INDICHROME_DRIVERS: frozenset[str] = frozenset(
    {
        EPM_GAMUT_OUT_OF_REACH,
        EPM_SPOT_COUNT_HIGH,
        "LPDF_EPM_005",  # spot K-dependent fallback
        "LPDF_EPM_011",  # spot fidelity risk
    }
)


def _classify(code: str) -> EpmTier | None:
    """Return the tier for a code, or None if it isn't an EPM finding."""
    if code in TIER_A_CODES or code in _LEGACY_TIER_A:
        return EpmTier.REJECT  # marker; tier-A always rejects
    if code in TIER_B_CODES or code in _LEGACY_TIER_B:
        return EpmTier.MARGINAL  # marker; B accumulates
    if code in TIER_C_CODES or code in _LEGACY_TIER_C:
        return EpmTier.PASS_WITH_ADVISORY  # marker; C only advises
    return None


def score_epm_candidacy(fired_codes: list[str] | tuple[str, ...]) -> EpmVerdict:
    """Decide EPM eligibility from the list of fired EPM inspection ids.

    Pure / deterministic: same input → same output. Caller hands in
    the codes that fired on the job (typically by filtering the
    ``LPDF_EPM_*`` prefix off the full finding list).
    """
    a_drivers: list[str] = []
    b_drivers: list[str] = []
    advisories: list[str] = []
    legacy_fired: list[str] = []

    seen: set[str] = set()
    for code in fired_codes:
        if code in seen:
            continue
        seen.add(code)
        tier = _classify(code)
        if tier is None:
            continue
        if code.startswith("LPDF_EPM_") and not code.endswith("_REJECT"):
            legacy_fired.append(code)
        if tier == EpmTier.REJECT:
            a_drivers.append(code)
        elif tier == EpmTier.MARGINAL:
            b_drivers.append(code)
        elif tier == EpmTier.PASS_WITH_ADVISORY:
            advisories.append(code)

    # A-tier wins outright.
    if a_drivers:
        all_drivers = tuple(a_drivers + b_drivers)
        return EpmVerdict(
            tier=EpmTier.REJECT,
            rejection_drivers=all_drivers,
            advisories=tuple(advisories),
            recommends_indichrome=any(d in _INDICHROME_DRIVERS for d in all_drivers),
            legacy_codes_fired=tuple(legacy_fired),
        )

    # >= 2 B-tier findings → reject.
    if len(b_drivers) >= 2:
        return EpmVerdict(
            tier=EpmTier.REJECT,
            rejection_drivers=tuple(b_drivers),
            advisories=tuple(advisories),
            recommends_indichrome=any(d in _INDICHROME_DRIVERS for d in b_drivers),
            legacy_codes_fired=tuple(legacy_fired),
        )

    # Exactly 1 B-tier → marginal.
    if len(b_drivers) == 1:
        return EpmVerdict(
            tier=EpmTier.MARGINAL,
            rejection_drivers=tuple(b_drivers),
            advisories=tuple(advisories),
            recommends_indichrome=any(d in _INDICHROME_DRIVERS for d in b_drivers),
            legacy_codes_fired=tuple(legacy_fired),
        )

    # No A or B; advisories only.
    if advisories:
        return EpmVerdict(
            tier=EpmTier.PASS_WITH_ADVISORY,
            advisories=tuple(advisories),
            legacy_codes_fired=tuple(legacy_fired),
        )

    # Clean.
    return EpmVerdict(
        tier=EpmTier.PASS,
        legacy_codes_fired=tuple(legacy_fired),
    )


__all__ = ["EpmTier", "EpmVerdict", "score_epm_candidacy"]
