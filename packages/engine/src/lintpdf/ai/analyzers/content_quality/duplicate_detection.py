"""Duplicate page detection via perceptual hashing.

Renders each page to an image, computes pHash, and compares Hamming distances
to identify near-duplicate pages within the same document.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Optional dependency
try:
    import imagehash

    _HAS_IMAGEHASH = True
except ImportError:
    imagehash = None
    _HAS_IMAGEHASH = False

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    PILImage = None  # type: ignore[assignment]
    _HAS_PIL = False

# Hamming distance threshold: below this value pages are considered near-duplicates
_DUPLICATE_THRESHOLD = 5


@register_ai_analyzer
class DuplicateDetectionAnalyzer(BaseAIAnalyzer):
    """Detect near-duplicate pages using perceptual hashing (pHash)."""

    category = "content_quality"
    feature_slug = "duplicate_detection"
    tier = "cpu"
    credits_per_run = 1

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        if not _HAS_IMAGEHASH or not _HAS_PIL:
            logger.debug("imagehash or Pillow not installed — skipping duplicate detection")
            return []

        from lintpdf.ai.rendering import render_all_pages

        try:
            page_images = render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("PDF rendering backend unavailable — skipping duplicate detection")
            return []

        if len(page_images) < 2:
            return []

        # Compute perceptual hashes
        hashes: list[tuple[int, imagehash.ImageHash]] = []
        for idx, png_bytes in enumerate(page_images):
            page_num = idx + 1
            try:
                img = PILImage.open(io.BytesIO(png_bytes))
                phash = imagehash.phash(img)
                hashes.append((page_num, phash))
            except Exception:
                logger.debug("Failed to compute pHash for page %d", page_num)

        # Compare all pairs
        findings: list[Finding] = []
        reported_pairs: set[tuple[int, int]] = set()

        for i, (page_a, hash_a) in enumerate(hashes):
            for j in range(i + 1, len(hashes)):
                page_b, hash_b = hashes[j]
                distance = hash_a - hash_b  # Hamming distance

                if distance < _DUPLICATE_THRESHOLD:
                    pair = (page_a, page_b)
                    if pair in reported_pairs:
                        continue
                    reported_pairs.add(pair)

                    # Similarity as a percentage (64-bit hash)
                    similarity = round((1.0 - distance / 64.0) * 100, 1)

                    findings.append(
                        self._make_finding(
                            inspection_id="AI_DUP_001",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Pages {page_a} and {page_b} are near-duplicates "
                                f"(similarity {similarity}%, Hamming distance {distance})"
                            ),
                            page_num=page_a,
                            details={
                                "duplicate_page": page_b,
                                "hamming_distance": distance,
                                "similarity_pct": similarity,
                            },
                        )
                    )

        return findings
