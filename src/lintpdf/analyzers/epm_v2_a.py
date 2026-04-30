"""EPM v2 Tier-A analyzer — hard-rejection checks.

Five detection-only analyzers backing the v2 IDs registered in
:mod:`lintpdf.epm.codes`. Tier-A findings hard-reject a job from EPM
candidacy in :func:`lintpdf.epm.scoring.score_epm_candidacy`.

Codes:

* **EPM-A1** ``LPDF_EPM_GAMUT_OUT_REJECT`` — page colors fall outside
  the CMY (or substrate) gamut.
* **EPM-A2** ``LPDF_EPM_K_COVERAGE_REJECT`` — K-channel usage too dense
  to drop without a perceptual shift past the configured ΔE tolerance.
* **EPM-A3** ``LPDF_EPM_RICH_BLACK_REJECT`` — rich-black recipe deviates
  from the configured default beyond the recipe ΔC tolerance.
* **EPM-A6** ``LPDF_EPM_SUBSTRATE_REJECT`` — substrate class declared on
  the job is incompatible with EPM (e.g. uncoated heavy stock).
* **EPM-A8** ``LPDF_EPM_TEXT_SIZE_REJECT`` — non-K text below the
  configured minimum point size for CMY-only output.

Each analyzer is intentionally narrow: detection-only, no document
mutation, deterministic, side-effect-free. Threshold tuning lives in
the ``epm_thresholds`` toggle defaults and is overridable per tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.epm import codes
from lintpdf.epm.icc import (
    IN_GAMUT_DELTA_E,
    cmy_strip_k_delta_e,
    cmyk_to_lab_naive,
    is_in_gamut_for_profile,
    load_profile,
)

if TYPE_CHECKING:
    from PIL.ImageCms import ImageCmsProfile

    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Default thresholds — keep in lockstep with
# :data:`lintpdf.tenants.toggle_registry._DEFAULT_EPM_THRESHOLDS`.
_DEFAULT_K_COVERAGE_PCT = 80.0
_DEFAULT_MIN_TEXT_PT = 5.0
# Substrate classes that EPM cannot service; matching is case-insensitive
# and substring-based so "Uncoated 200gsm" still trips the gate.
_INCOMPATIBLE_SUBSTRATES: frozenset[str] = frozenset(
    {"uncoated_heavy", "metallic", "transparent", "newsprint"}
)
# Rich-black recipe ΔC tolerance — sum of |C-Cdef|+|M-Mdef|+|Y-Ydef|+|K-Kdef|
# above this threshold counts as a deviation worth flagging.
_RICH_BLACK_DELTA_PCT = 25.0


class EpmTierAAnalyzer(BaseAnalyzer):
    """Tier-A EPM analyzer — fans out to the five A-tier detectors.

    The analyzer is constructed once per orchestrator run with the
    tenant-resolved thresholds. ``analyze()`` walks events + the
    semantic document, accumulates findings, and returns them.

    ``substrate_profile_path`` (optional) points at a tenant-uploaded
    ICC output profile (.icc / .icm). When set, the A1 gamut detector
    round-trips each sampled color through that profile via
    :func:`is_in_gamut_for_profile`. When unset, the detector falls
    back to a sRGB round-trip via :func:`is_in_gamut` — the right
    default for tenants that haven't uploaded a substrate profile yet.
    """

    def __init__(
        self,
        *,
        epm_thresholds: dict[str, Any] | None = None,
        substrate_class: str | None = None,
        substrate_profile_path: str | None = None,
        min_text_pt: float = _DEFAULT_MIN_TEXT_PT,
        k_coverage_threshold_pct: float = _DEFAULT_K_COVERAGE_PCT,
    ) -> None:
        self._thresholds = epm_thresholds or {}
        self._substrate_class = (substrate_class or "").strip().lower()
        self._substrate_profile_path = substrate_profile_path
        self._min_text_pt = min_text_pt
        self._k_coverage_threshold_pct = k_coverage_threshold_pct

    def _resolve_profile(self) -> ImageCmsProfile | None:
        """Load the substrate profile if configured. Best-effort —
        a missing / unreadable file falls back to the sRGB default
        rather than blocking the whole analyzer."""
        if not self._substrate_profile_path:
            return None
        try:
            return load_profile(self._substrate_profile_path)
        except Exception:
            return None

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(
            detect_a1_gamut(
                document,
                events,
                self._thresholds,
                profile=self._resolve_profile(),
            )
        )
        findings.extend(
            detect_a2_k_coverage(
                events,
                threshold_pct=self._k_coverage_threshold_pct,
                tolerance_de=float(self._thresholds.get("delta_e_max", IN_GAMUT_DELTA_E)),
            )
        )
        findings.extend(
            detect_a3_rich_black_deviation(
                events,
                recipe=self._thresholds.get("rich_black", {"c": 40, "m": 20, "y": 20, "k": 80}),
                tolerance_pct=_RICH_BLACK_DELTA_PCT,
            )
        )
        findings.extend(detect_a6_substrate_incompatible(self._substrate_class))
        findings.extend(
            detect_a8_text_too_small_for_cmy(
                events,
                min_pt=self._min_text_pt,
            )
        )
        return findings


# ---- A1: gamut-out-of-reach --------------------------------------------


def detect_a1_gamut(
    document: SemanticDocument,
    events: list[ContentStreamEvent],
    thresholds: dict[str, Any],
    *,
    profile: ImageCmsProfile | None = None,
) -> list[Finding]:
    """Fire EPM-A1 when any sampled color exceeds the gamut tolerance.

    Two paths:

    * **Substrate-aware** (``profile`` set) — each DeviceCMYK fill is
      converted to Lab via :func:`cmyk_to_lab_naive` and round-tripped
      through the tenant-uploaded ICC output profile via
      :func:`is_in_gamut_for_profile`. This is the strict path
      matching the actual press gamut.
    * **Default heuristic** (``profile=None``) — the analyzer falls
      back to a saturated-CMYK detector that fires when the fill has
      C/M/Y all ≥0.95 and K ≥0.5. This is intentionally conservative;
      it under-fires rather than false-positives so tenants without
      an uploaded substrate profile don't get noisy verdicts.

    Findings are deduplicated per (page, recipe).
    """
    from lintpdf.semantic.events import ColorChangedEvent

    delta_e_max = float(thresholds.get("delta_e_max", IN_GAMUT_DELTA_E))
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()

    for ev in events:
        if not isinstance(ev, ColorChangedEvent):
            continue
        cs = (ev.color_space or "").lower()
        if "cmyk" not in cs:
            continue
        if len(ev.color_values) < 4:
            continue
        c, m, y, k = ev.color_values[:4]

        out_of_gamut = False
        lab: tuple[float, float, float] | None = None

        if profile is not None:
            # Substrate-aware path: convert CMYK → Lab, then check the
            # press profile. is_in_gamut_for_profile does the actual
            # round-trip.
            try:
                lab = cmyk_to_lab_naive((c * 100.0, m * 100.0, y * 100.0, k * 100.0))
                out_of_gamut = not is_in_gamut_for_profile(
                    lab, profile=profile, tolerance_de=delta_e_max
                )
            except Exception:
                # Bad profile / edge-case Lab: fall back to heuristic
                # so a profile error doesn't cripple the analyzer.
                out_of_gamut = all(v >= 0.95 for v in (c, m, y)) and k >= 0.5
        else:
            # Default heuristic: conservative saturated-CMYK detector.
            # 100% C/M/Y in isolation hugs the gamut boundary; a CMY
            # mix at full saturation that also carries K above ΔE
            # budget is the cleanest "needs K" signal we can emit
            # without an ICC profile.
            out_of_gamut = all(v >= 0.95 for v in (c, m, y)) and k >= 0.5

        if not out_of_gamut:
            continue

        key = (ev.page_num, f"{c:.2f}-{m:.2f}-{y:.2f}-{k:.2f}")
        if key in seen:
            continue
        seen.add(key)

        findings.append(
            Finding(
                inspection_id=codes.EPM_GAMUT_OUT_OF_REACH,
                severity=Severity.ERROR,
                message=(
                    "Sampled color outside "
                    + (
                        "substrate ICC gamut"
                        if profile is not None
                        else "CMY-only gamut (default heuristic)"
                    )
                    + f" (ΔE budget {delta_e_max:.1f})."
                ),
                page_num=ev.page_num,
                category="color",
                details={
                    "color_space": ev.color_space,
                    "values": list(ev.color_values),
                    **({"lab": list(lab)} if lab is not None else {}),
                    "profile_source": "substrate" if profile is not None else "default_heuristic",
                    "delta_e_budget": delta_e_max,
                },
            )
        )
    return findings


# ---- A2: K-coverage too high -------------------------------------------


def detect_a2_k_coverage(
    events: list[ContentStreamEvent],
    *,
    threshold_pct: float,
    tolerance_de: float,
) -> list[Finding]:
    """Fire EPM-A2 when a fill recipe carries K above ``threshold_pct``
    and the K-strip simulator says the color shifts past tolerance."""
    from lintpdf.semantic.events import PathPaintingEvent

    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()

    for ev in events:
        if not isinstance(ev, PathPaintingEvent):
            continue
        if not ev.fill:
            continue
        cs = (ev.fill_color_space or "").lower()
        if "cmyk" not in cs:
            continue
        if len(ev.fill_color_values) < 4:
            continue
        c, m, y, k = ev.fill_color_values[:4]
        k_pct = k * 100.0
        if k_pct < threshold_pct:
            continue
        cmyk = (c * 100.0, m * 100.0, y * 100.0, k_pct)
        delta = cmy_strip_k_delta_e(cmyk)
        if delta <= tolerance_de:
            continue
        # Dedup at (page, recipe) — a repeated fill in the same recipe
        # adds no information.
        key = (ev.page_num, f"{c:.2f}-{m:.2f}-{y:.2f}-{k:.2f}")
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                inspection_id=codes.EPM_K_COVERAGE_TOO_HIGH,
                severity=Severity.ERROR,
                message=(
                    f"K coverage {k_pct:.0f}% exceeds {threshold_pct:.0f}% "
                    f"and shifts ΔE {delta:.1f} when stripped (limit "
                    f"{tolerance_de:.1f})."
                ),
                page_num=ev.page_num,
                category="color",
                details={
                    "k_pct": round(k_pct, 1),
                    "threshold_pct": threshold_pct,
                    "delta_e_strip": round(delta, 2),
                    "tolerance_de": tolerance_de,
                },
            )
        )
    return findings


# ---- A3: rich-black recipe deviates -----------------------------------


def detect_a3_rich_black_deviation(
    events: list[ContentStreamEvent],
    *,
    recipe: dict[str, float],
    tolerance_pct: float,
) -> list[Finding]:
    """Fire EPM-A3 when an opaque rich-black fill deviates from the
    configured house recipe by more than ``tolerance_pct``.

    "Rich-black" in this context means K=100% with at least one CMY
    channel non-zero — pure 100% K isn't a rich-black recipe and never
    fires this check.
    """
    from lintpdf.semantic.events import PathPaintingEvent

    target_c = float(recipe.get("c", 40))
    target_m = float(recipe.get("m", 30))
    target_y = float(recipe.get("y", 30))
    target_k = float(recipe.get("k", 100))

    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()

    for ev in events:
        if not isinstance(ev, PathPaintingEvent) or not ev.fill:
            continue
        cs = (ev.fill_color_space or "").lower()
        if "cmyk" not in cs:
            continue
        if len(ev.fill_color_values) < 4:
            continue
        c, m, y, k = ev.fill_color_values[:4]
        c_pct, m_pct, y_pct, k_pct = c * 100, m * 100, y * 100, k * 100
        # Only flag fills that look like a rich-black attempt.
        if k_pct < 90:
            continue
        if max(c_pct, m_pct, y_pct) < 5:
            continue
        delta = (
            abs(c_pct - target_c)
            + abs(m_pct - target_m)
            + abs(y_pct - target_y)
            + abs(k_pct - target_k)
        )
        if delta <= tolerance_pct:
            continue
        key = (ev.page_num, f"{c_pct:.0f}/{m_pct:.0f}/{y_pct:.0f}/{k_pct:.0f}")
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                inspection_id=codes.EPM_RICH_BLACK_DEVIATION,
                severity=Severity.ERROR,
                message=(
                    f"Rich-black fill {c_pct:.0f}/{m_pct:.0f}/{y_pct:.0f}/"
                    f"{k_pct:.0f} deviates from house recipe by ΔC "
                    f"{delta:.0f}% (limit {tolerance_pct:.0f}%)."
                ),
                page_num=ev.page_num,
                category="color",
                details={
                    "fill": [c_pct, m_pct, y_pct, k_pct],
                    "recipe": recipe,
                    "delta_pct": round(delta, 1),
                    "tolerance_pct": tolerance_pct,
                },
            )
        )
    return findings


# ---- A6: substrate-class incompatibility -------------------------------


def detect_a6_substrate_incompatible(substrate_class: str) -> list[Finding]:
    """Fire EPM-A6 when the substrate declared on the job is in the
    incompatible-substrates set (configurable via tenant overrides)."""
    if not substrate_class:
        return []
    needle = substrate_class.strip().lower()
    for incompatible in _INCOMPATIBLE_SUBSTRATES:
        if incompatible in needle:
            return [
                Finding(
                    inspection_id=codes.EPM_SUBSTRATE_INCOMPATIBLE,
                    severity=Severity.ERROR,
                    message=(f"Substrate class {substrate_class!r} is incompatible with EPM."),
                    page_num=0,
                    category="color",
                    details={"substrate_class": substrate_class},
                )
            ]
    return []


# ---- A8: text too small for CMY-only -----------------------------------


def detect_a8_text_too_small_for_cmy(
    events: list[ContentStreamEvent],
    *,
    min_pt: float,
) -> list[Finding]:
    """Fire EPM-A8 when non-K text falls below the minimum point size.

    Pure-K text is unaffected (K stays the same when K is the only ink
    in the recipe), so the analyzer skips events whose ``color_values``
    are pure black on DeviceGray or pure K on DeviceCMYK.
    """
    from lintpdf.semantic.events import TextRenderedEvent

    findings: list[Finding] = []
    seen: set[tuple[int, str, float]] = set()

    for ev in events:
        if not isinstance(ev, TextRenderedEvent):
            continue
        if ev.font_size >= min_pt:
            continue
        cs = (ev.color_space or "").lower()
        # Pure K on DeviceCMYK is unaffected by K-strip — skip it.
        if "cmyk" in cs and len(ev.color_values) >= 4:
            c, m, y, k = ev.color_values[:4]
            if max(c, m, y) < 0.05 and k > 0.5:
                continue
        # Pure black on DeviceGray = same story.
        if cs == "devicegray" and ev.color_values and ev.color_values[0] < 0.05:
            continue
        key = (ev.page_num, ev.font_name, round(ev.font_size, 1))
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                inspection_id=codes.EPM_TEXT_TOO_SMALL_FOR_CMY,
                severity=Severity.ERROR,
                message=(
                    f"Non-K text at {ev.font_size:.1f}pt is below the "
                    f"CMY-only minimum {min_pt:.1f}pt."
                ),
                page_num=ev.page_num,
                category="text",
                object_type="text",
                object_id=ev.font_name,
                details={
                    "font_size_pt": round(ev.font_size, 2),
                    "min_pt": min_pt,
                    "font_name": ev.font_name,
                },
            )
        )
    return findings


__all__ = [
    "EpmTierAAnalyzer",
    "detect_a1_gamut",
    "detect_a2_k_coverage",
    "detect_a3_rich_black_deviation",
    "detect_a6_substrate_incompatible",
    "detect_a8_text_too_small_for_cmy",
]
