"""Version diff analyzer — compare current file against a reference version.

Renders pages from both files and computes structural similarity (SSIM)
per page to identify visual differences between revisions.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import numpy as np
    from skimage.metrics import structural_similarity as ssim

    _HAS_SKIMAGE = True
except ImportError:
    ssim = None
    np = None
    _HAS_SKIMAGE = False

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    PILImage = None  # type: ignore[assignment]
    _HAS_PIL = False


def _png_to_grayscale_array(png_bytes: bytes) -> Any:
    """Convert PNG bytes to a grayscale NumPy array."""
    img = PILImage.open(io.BytesIO(png_bytes)).convert("L")
    return np.array(img)


@register_ai_analyzer
class VersionDiffAnalyzer(BaseAIAnalyzer):
    """Compare current document against a reference version using SSIM."""

    category = "file_comparison"
    feature_slug = "version_diff"
    tier = "cpu"
    credits_per_run = 1

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        # Check for reference file configuration
        reference_pdf_bytes = self._get_reference_bytes(ai_config)

        if reference_pdf_bytes is None:
            return [
                self._make_finding(
                    inspection_id="AI_VDIFF_001",
                    severity=Severity.ADVISORY,
                    message=(
                        "No reference file provided for version comparison. "
                        "Configure a reference file ID in AI settings to enable diff."
                    ),
                    details={"reason": "no_reference_file"},
                )
            ]

        if not _HAS_SKIMAGE or not _HAS_PIL:
            logger.debug("scikit-image or Pillow not installed — skipping version diff")
            return []

        from lintpdf.ai.rendering import render_all_pages

        try:
            current_pages = render_all_pages(pdf_bytes, dpi=150)
            reference_pages = render_all_pages(reference_pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("PDF rendering backend unavailable — skipping version diff")
            return []

        findings: list[Finding] = []
        _max_pages = max(len(current_pages), len(reference_pages))

        # Report page count difference
        if len(current_pages) != len(reference_pages):
            findings.append(
                self._make_finding(
                    inspection_id="AI_VDIFF_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page count changed: reference has {len(reference_pages)} "
                        f"page(s), current has {len(current_pages)} page(s)"
                    ),
                    details={
                        "reference_pages": len(reference_pages),
                        "current_pages": len(current_pages),
                    },
                )
            )

        # Compare each page pair
        for i in range(min(len(current_pages), len(reference_pages))):
            page_num = i + 1
            try:
                current_arr = _png_to_grayscale_array(current_pages[i])
                ref_arr = _png_to_grayscale_array(reference_pages[i])

                # Resize reference to match current if dimensions differ
                if current_arr.shape != ref_arr.shape:
                    ref_img = PILImage.fromarray(ref_arr).resize(
                        (current_arr.shape[1], current_arr.shape[0]),
                        PILImage.Resampling.LANCZOS,
                    )
                    ref_arr = np.array(ref_img)

                score, diff_image = ssim(ref_arr, current_arr, full=True)
                score = round(float(score), 4)

                # Identify changed regions (where SSIM < 0.8)
                changed_pixels = int(np.sum(diff_image < 0.8))
                total_pixels = diff_image.size
                change_pct = (
                    round(changed_pixels / total_pixels * 100, 2) if total_pixels > 0 else 0.0
                )

                if score < 0.999:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_VDIFF_003",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Page {page_num} differs from reference "
                                f"(SSIM={score:.4f}, {change_pct}% pixels changed)"
                            ),
                            page_num=page_num,
                            details={
                                "ssim_score": score,
                                "changed_pixels": changed_pixels,
                                "total_pixels": total_pixels,
                                "change_pct": change_pct,
                            },
                        )
                    )
            except Exception:
                logger.debug("SSIM comparison failed for page %d", page_num)

        return findings

    @staticmethod
    def _get_reference_bytes(ai_config: TenantAIConfig | None) -> bytes | None:
        """Retrieve reference PDF bytes from configuration.

        Resolution order:
        1. Pre-attached bytes on ``ai_config._reference_pdf_bytes`` (set by orchestrator).
        2. ``reference_file_id`` in ai_config details → fetch from object storage.
        """
        if ai_config is None:
            return None

        # Fast path: orchestrator already resolved and attached bytes
        reference_bytes: bytes | None = getattr(ai_config, "_reference_pdf_bytes", None)
        if reference_bytes and isinstance(reference_bytes, bytes):
            return reference_bytes

        # Slow path: resolve reference_file_id from storage
        details = getattr(ai_config, "details", None) or {}
        file_id = details.get("reference_file_id") if isinstance(details, dict) else None
        if not file_id:
            return None

        try:
            from lintpdf.api.storage import get_storage_backend

            storage = get_storage_backend()
            ref_bytes = storage.download(str(file_id))
            if ref_bytes and isinstance(ref_bytes, bytes):
                return ref_bytes
        except Exception:
            logger.debug("Failed to resolve reference_file_id=%s from storage", file_id)

        return None
