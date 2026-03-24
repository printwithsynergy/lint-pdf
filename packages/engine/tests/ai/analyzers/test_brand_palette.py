"""Tests for BrandPaletteAnalyzer with color matching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lintpdf.analyzers.finding import Severity


class TestBrandPaletteAnalyzer:
    """Tests for brand palette compliance checking."""

    @staticmethod
    def test_no_palette_configured_returns_advisory(minimal_semantic_doc: MagicMock) -> None:
        ai_config = MagicMock()
        ai_config.brand_palette = None

        with (
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_COLOUR",
                True,
            ),
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_NUMPY",
                True,
            ),
        ):
            from lintpdf.ai.analyzers.color_compliance.brand_palette import (
                BrandPaletteAnalyzer,
            )

            analyzer = BrandPaletteAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf", ai_config=ai_config)

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_BRAND_001"
        assert findings[0].severity == Severity.ADVISORY
        assert "No brand palette" in findings[0].message

    @staticmethod
    def test_empty_palette_returns_advisory(minimal_semantic_doc: MagicMock) -> None:
        ai_config = MagicMock()
        ai_config.brand_palette = []

        with (
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_COLOUR",
                True,
            ),
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_NUMPY",
                True,
            ),
        ):
            from lintpdf.ai.analyzers.color_compliance.brand_palette import (
                BrandPaletteAnalyzer,
            )

            analyzer = BrandPaletteAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf", ai_config=ai_config)

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_BRAND_001"

    @staticmethod
    def test_skips_when_colour_science_not_installed(minimal_semantic_doc: MagicMock) -> None:
        with patch(
            "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_COLOUR",
            False,
        ):
            from lintpdf.ai.analyzers.color_compliance.brand_palette import (
                BrandPaletteAnalyzer,
            )

            analyzer = BrandPaletteAnalyzer()
            findings = analyzer.analyze(
                minimal_semantic_doc, [], b"fake_pdf", ai_config=MagicMock()
            )

        assert findings == []

    @staticmethod
    def test_none_ai_config_returns_advisory(minimal_semantic_doc: MagicMock) -> None:
        with (
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_COLOUR",
                True,
            ),
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_NUMPY",
                True,
            ),
        ):
            from lintpdf.ai.analyzers.color_compliance.brand_palette import (
                BrandPaletteAnalyzer,
            )

            analyzer = BrandPaletteAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf", ai_config=None)

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_BRAND_001"

    @staticmethod
    def test_findings_have_ai_source(minimal_semantic_doc: MagicMock) -> None:
        ai_config = MagicMock()
        ai_config.brand_palette = None

        with (
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_COLOUR",
                True,
            ),
            patch(
                "lintpdf.ai.analyzers.color_compliance.brand_palette._HAS_NUMPY",
                True,
            ),
        ):
            from lintpdf.ai.analyzers.color_compliance.brand_palette import (
                BrandPaletteAnalyzer,
            )

            analyzer = BrandPaletteAnalyzer()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf", ai_config=ai_config)

        for f in findings:
            assert f.source == "ai"
            assert f.category == "color_compliance"

    @staticmethod
    def test_analyzer_metadata() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            BrandPaletteAnalyzer,
        )

        analyzer = BrandPaletteAnalyzer()
        assert analyzer.category == "color_compliance"
        assert analyzer.feature_slug == "brand_palette_check"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1


class TestParseColorValue:
    """Tests for the _parse_color_value helper."""

    @staticmethod
    def test_parse_hex_6_digit() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        result = _parse_color_value("#FF0000")
        assert result is not None
        r, g, b = result
        assert abs(r - 1.0) < 0.01
        assert abs(g - 0.0) < 0.01
        assert abs(b - 0.0) < 0.01

    @staticmethod
    def test_parse_hex_3_digit() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        result = _parse_color_value("#F00")
        assert result is not None
        r, g, _b = result
        assert abs(r - 1.0) < 0.01
        assert abs(g - 0.0) < 0.01

    @staticmethod
    def test_parse_rgb() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        result = _parse_color_value("rgb(255, 0, 0)")
        assert result is not None
        r, _g, _b = result
        assert abs(r - 1.0) < 0.01

    @staticmethod
    def test_parse_cmyk() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        result = _parse_color_value("cmyk(0, 100, 100, 0)")
        assert result is not None
        r, g, _b = result
        assert abs(r - 1.0) < 0.01
        assert abs(g - 0.0) < 0.01

    @staticmethod
    def test_parse_invalid_returns_none() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        assert _parse_color_value("not_a_color") is None
        assert _parse_color_value("") is None

    @staticmethod
    def test_parse_hex_with_whitespace() -> None:
        from lintpdf.ai.analyzers.color_compliance.brand_palette import (
            _parse_color_value,
        )

        result = _parse_color_value("  #00FF00  ")
        assert result is not None
        _, g, _ = result
        assert abs(g - 1.0) < 0.01
