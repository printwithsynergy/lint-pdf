"""Image effective-DPI analyzer — reads codex extraction signals.

Consumes ``CodexDocument.images[*].effective_resolution_dpi`` from the
codex-pdf extraction payload and flags images whose effective (placed)
DPI is below the minimum threshold.

Effective DPI accounts for scale: a 300 DPI image enlarged 2× prints
at 150 DPI. Codex computes this from the actual placed rect using
``page.get_image_rects()`` (v1.17.0+).

Check IDs (same codes as ImageAnalyzer, distinct source='codex'):
    LPDF_IMG_001  — effective DPI below minimum (default 150)
    LPDF_IMG_006  — image upscaled >200%
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lintpdf.ai.analyzers.codex_signals._common import codex_payload
from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# Default DPI thresholds — match the raw-PDF ImageAnalyzer defaults.
_DEFAULT_MIN_DPI = 150.0
# Upscale threshold: placed size / natural size > this fraction → flag.
_UPSCALE_THRESHOLD_PCT = 200.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@register_ai_analyzer
class ImageResolutionAnalyzer(BaseAIAnalyzer):
    """Read codex's effective_resolution_dpi per image and flag low-DPI placements.

    Codex v1.17.0 exposes ``effective_resolution_dpi`` (x_dpi, y_dpi) and
    ``placed_width_pts`` / ``placed_height_pts`` for every image placement.
    This analyzer reads those fields from ``ctx.config["codex_payload"]``
    and emits:

    - LPDF_IMG_001 — effective DPI below minimum (error if <100, warning if <150).
    - LPDF_IMG_006 — image placed at >200% of its natural pixel size (upscaled).

    Emits zero findings when codex is unreachable or the payload predates
    v1.17.0 (graceful degradation; the raw-PDF ImageAnalyzer covers that path).
    """

    category = "codex_signals"
    feature_slug = "codex_image_resolution"
    tier = "cpu"
    credits_per_run = 0  # reads already-extracted JSON; no external calls

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None:
            return []

        images = payload.get("images")
        if not isinstance(images, list) or not images:
            return []

        min_dpi = _safe_float(
            ctx.config.get("image_resolution", {}).get("min_dpi"),
            _DEFAULT_MIN_DPI,
        )

        findings: list[Finding] = []
        for img in images:
            if not isinstance(img, dict):
                continue
            findings.extend(self._check_image(img, min_dpi))

        return findings

    def _check_image(self, img: dict[str, Any], min_dpi: float) -> list[Finding]:
        findings: list[Finding] = []

        image_id = img.get("image_id") or img.get("name") or "unknown"
        page_num = img.get("page_num")
        if not isinstance(page_num, int):
            page_num = 0

        effective_dpi = img.get("effective_resolution_dpi")
        width_px = _safe_float(img.get("width_px"), 0.0)
        placed_width_pts = img.get("placed_width_pts")

        # --- LPDF_IMG_001: low effective DPI ---
        if isinstance(effective_dpi, dict):
            x_dpi = _safe_float(effective_dpi.get("x_dpi"), 0.0)
            y_dpi = _safe_float(effective_dpi.get("y_dpi"), 0.0)
            if x_dpi > 0.0 and y_dpi > 0.0:
                dpi_effective = min(x_dpi, y_dpi)
                if dpi_effective < min_dpi:
                    severity = Severity.ERROR if dpi_effective < 100.0 else Severity.WARNING
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_IMG_001",
                            severity=severity,
                            message=(
                                f"Image '{image_id}' has low effective resolution: "
                                f"{dpi_effective:.0f} DPI "
                                f"(minimum {min_dpi:.0f} DPI)"
                            ),
                            page_num=page_num,
                            details={
                                "image_id": image_id,
                                "dpi_x": x_dpi,
                                "dpi_y": y_dpi,
                                "dpi_effective": dpi_effective,
                                "min_dpi": min_dpi,
                                "source": "codex",
                            },
                            iso_clause="ISO 32000-2:2020 8.9",
                            object_id=str(image_id),
                            object_type="image",
                        )
                    )

        # --- LPDF_IMG_006: upscaled >200% ---
        if (
            isinstance(placed_width_pts, (int, float))
            and width_px > 0.0
        ):
            placed_w = float(placed_width_pts)
            # Natural width in points at 72 ppi: width_px / 72 * 72 = width_px pts
            natural_width_pts = width_px  # pixels == points at the PDF 72 ppi base
            if natural_width_pts > 0.0:
                scale_pct = (placed_w / natural_width_pts) * 100.0
                if scale_pct > _UPSCALE_THRESHOLD_PCT:
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_IMG_006",
                            severity=Severity.WARNING,
                            message=(
                                f"Image '{image_id}' is upscaled "
                                f"{scale_pct:.0f}% on page {page_num} "
                                f"(>{_UPSCALE_THRESHOLD_PCT:.0f}% causes visible quality loss)"
                            ),
                            page_num=page_num,
                            details={
                                "image_id": image_id,
                                "upscale_percent": round(scale_pct, 1),
                                "placed_width_pts": placed_w,
                                "width_px": width_px,
                                "source": "codex",
                            },
                            object_id=str(image_id),
                            object_type="image",
                        )
                    )

        return findings
