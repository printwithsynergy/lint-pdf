"""Tests for DuplicateDetectionAnalyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from siftpdf.analyzers.finding import Severity
from siftpdf.plugin import AnalyzerContext


def _ctx(
    document: MagicMock,
    page_images: list[bytes] | None = None,
    render_raises: BaseException | None = None,
) -> AnalyzerContext:
    """Build an AnalyzerContext mirroring orchestrator-driven analyze_v2 calls.

    Phase 2 alpha-stream batch 3 migrated DuplicateDetectionAnalyzer
    from legacy analyze() to analyze_v2(ctx). Phase 2 beta-stream
    batch 3 routed render_all_pages through ctx.services.renderer,
    so the test harness must provide a services mock with a
    renderer that returns the desired page images (or raises).

    Pass ``page_images=[...]`` for happy-path tests, or
    ``render_raises=RuntimeError(...)`` to simulate a renderer
    backend failure. Pass neither and ``ctx.services`` is None,
    which causes the analyzer to self-skip.
    """
    services = None
    if page_images is not None or render_raises is not None:
        renderer = MagicMock()
        if render_raises is not None:
            renderer.render_all_pages.side_effect = render_raises
        else:
            renderer.render_all_pages.return_value = page_images
        services = MagicMock()
        services.renderer = renderer
    return AnalyzerContext(
        document=document,
        events=[],
        pdf_bytes=b"fake_pdf",
        services=services,
    )


class TestDuplicateDetectionAnalyzer:
    """Tests for DuplicateDetectionAnalyzer with mocked rendering and imagehash."""

    def test_returns_empty_when_imagehash_unavailable(
        self, minimal_semantic_doc: MagicMock
    ) -> None:
        with patch(
            "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
            False,
        ):
            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc))

        assert findings == []

    @staticmethod
    def test_returns_empty_when_pil_unavailable(minimal_semantic_doc: MagicMock) -> None:
        with patch(
            "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
            False,
        ):
            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc))

        assert findings == []

    @staticmethod
    def test_single_page_returns_empty(minimal_semantic_doc: MagicMock) -> None:
        """Duplicate detection requires at least 2 pages."""
        fake_png = b"\x89PNG_fake"

        with (
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
        ):
            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, page_images=[fake_png]))

        assert findings == []

    @staticmethod
    def test_detects_near_duplicate_pages(minimal_semantic_doc: MagicMock) -> None:
        """Two pages with identical hashes should be flagged."""
        fake_png = b"\x89PNG_fake"

        # Mock imagehash to return identical hashes for both pages
        mock_hash = MagicMock()
        mock_hash.__sub__ = MagicMock(return_value=0)  # Hamming distance 0

        with (
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection.imagehash"
            ) as mock_imagehash,
            patch("siftpdf.ai.analyzers.content_quality.duplicate_detection.PILImage") as mock_pil,
        ):
            mock_imagehash.phash.return_value = mock_hash
            mock_pil.open.return_value = MagicMock()

            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(
                _ctx(minimal_semantic_doc, page_images=[fake_png, fake_png])
            )

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DUP_001"
        assert findings[0].severity == Severity.ADVISORY
        assert findings[0].source == "ai"
        assert findings[0].category == "content_quality"
        assert "near-duplicates" in findings[0].message
        assert findings[0].details["similarity_pct"] == 100.0

    @staticmethod
    def test_no_duplicates_when_hashes_differ(minimal_semantic_doc: MagicMock) -> None:
        fake_png = b"\x89PNG_fake"

        mock_hash1 = MagicMock()
        mock_hash2 = MagicMock()
        # Hamming distance > threshold (5)
        mock_hash1.__sub__ = MagicMock(return_value=30)

        with (
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection.imagehash"
            ) as mock_imagehash,
            patch("siftpdf.ai.analyzers.content_quality.duplicate_detection.PILImage") as mock_pil,
        ):
            mock_imagehash.phash.side_effect = [mock_hash1, mock_hash2]
            mock_pil.open.return_value = MagicMock()

            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(
                _ctx(minimal_semantic_doc, page_images=[fake_png, fake_png])
            )

        assert len(findings) == 0

    @staticmethod
    def test_rendering_failure_returns_empty(minimal_semantic_doc: MagicMock) -> None:
        with (
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "siftpdf.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
        ):
            from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze_v2(
                _ctx(minimal_semantic_doc, render_raises=RuntimeError("No backend"))
            )

        assert findings == []

    @staticmethod
    def test_analyzer_metadata() -> None:
        from siftpdf.ai.analyzers.content_quality.duplicate_detection import (
            DuplicateDetectionAnalyzer,
        )

        analyzer = DuplicateDetectionAnalyzer()
        assert analyzer.category == "content_quality"
        assert analyzer.feature_slug == "duplicate_detection"
        assert analyzer.tier == "cpu"
