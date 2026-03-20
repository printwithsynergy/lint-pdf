"""Tests for DuplicateDetectionAnalyzer."""

from __future__ import annotations

# skipcq: PYL-R0201
from unittest.mock import MagicMock, patch

from grounded.analyzers.finding import Severity


class TestDuplicateDetectionAnalyzer:
    """Tests for DuplicateDetectionAnalyzer with mocked rendering and imagehash."""

    def test_returns_empty_when_imagehash_unavailable(
        self, minimal_semantic_doc: MagicMock
    ) -> None:
        with patch(
            "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
            False,
        ):
            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_returns_empty_when_pil_unavailable(self, minimal_semantic_doc: MagicMock) -> None:
        with patch(
            "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
            False,
        ):
            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_single_page_returns_empty(self, minimal_semantic_doc: MagicMock) -> None:
        """Duplicate detection requires at least 2 pages."""
        fake_png = b"\x89PNG_fake"

        with (
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "grounded.ai.rendering.render_all_pages",
                return_value=[fake_png],  # Only 1 page
            ),
        ):
            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_detects_near_duplicate_pages(self, minimal_semantic_doc: MagicMock) -> None:
        """Two pages with identical hashes should be flagged."""
        fake_png = b"\x89PNG_fake"

        # Mock imagehash to return identical hashes for both pages
        mock_hash = MagicMock()
        mock_hash.__sub__ = MagicMock(return_value=0)  # Hamming distance 0

        with (
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "grounded.ai.rendering.render_all_pages",
                return_value=[fake_png, fake_png],
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection.imagehash"
            ) as mock_imagehash,
            patch("grounded.ai.analyzers.content_quality.duplicate_detection.PILImage") as mock_pil,
        ):
            mock_imagehash.phash.return_value = mock_hash
            mock_pil.open.return_value = MagicMock()

            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DUP_001"
        assert findings[0].severity == Severity.ADVISORY
        assert findings[0].source == "ai"
        assert findings[0].category == "content_quality"
        assert "near-duplicates" in findings[0].message
        assert findings[0].details["similarity_pct"] == 100.0

    def test_no_duplicates_when_hashes_differ(self, minimal_semantic_doc: MagicMock) -> None:
        fake_png = b"\x89PNG_fake"

        mock_hash1 = MagicMock()
        mock_hash2 = MagicMock()
        # Hamming distance > threshold (5)
        mock_hash1.__sub__ = MagicMock(return_value=30)

        with (
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "grounded.ai.rendering.render_all_pages",
                return_value=[fake_png, fake_png],
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection.imagehash"
            ) as mock_imagehash,
            patch("grounded.ai.analyzers.content_quality.duplicate_detection.PILImage") as mock_pil,
        ):
            mock_imagehash.phash.side_effect = [mock_hash1, mock_hash2]
            mock_pil.open.return_value = MagicMock()

            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert len(findings) == 0

    def test_rendering_failure_returns_empty(self, minimal_semantic_doc: MagicMock) -> None:
        with (
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_IMAGEHASH",
                True,
            ),
            patch(
                "grounded.ai.analyzers.content_quality.duplicate_detection._HAS_PIL",
                True,
            ),
            patch(
                "grounded.ai.rendering.render_all_pages",
                side_effect=RuntimeError("No backend"),
            ),
        ):
            from grounded.ai.analyzers.content_quality.duplicate_detection import (
                DuplicateDetectionAnalyzer,
            )

            analyzer = DuplicateDetectionAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_analyzer_metadata(self) -> None:
        from grounded.ai.analyzers.content_quality.duplicate_detection import (
            DuplicateDetectionAnalyzer,
        )

        analyzer = DuplicateDetectionAnalyzer()
        assert analyzer.category == "content_quality"
        assert analyzer.feature_slug == "duplicate_detection"
        assert analyzer.tier == "cpu"
