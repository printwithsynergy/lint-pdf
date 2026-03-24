"""Tests for DielineByNameAnalyzer."""

from __future__ import annotations

from unittest.mock import MagicMock

from lintpdf.analyzers.finding import Severity


def _doc_with_layers(
    layer_names: list[str] | None = None,
    spot_color_names: list[str] | None = None,
    industry_type: str | None = None,
) -> tuple[MagicMock, MagicMock | None]:
    """Create a SemanticDocument mock with specified layers and spot colors.

    Returns (doc, ai_config).
    """
    doc = MagicMock()
    doc.page_count = 1
    doc.version = "1.7"
    doc.is_encrypted = False

    # Catalog with OCG layers
    if layer_names:
        doc.catalog = {
            "OCProperties": {
                "OCGs": [{"Name": name} for name in layer_names],
            }
        }
    else:
        doc.catalog = {}

    # Pages with color spaces
    page = MagicMock()
    page.page_num = 1
    page.color_spaces = {}
    page.resources = {}

    if spot_color_names:
        for i, name in enumerate(spot_color_names):
            cs_mock = MagicMock()
            cs_mock.cs_type = "Separation"
            cs_mock.colorant_names = [name]
            page.color_spaces[f"CS{i}"] = cs_mock

    doc.pages = [page]

    ai_config = None
    if industry_type:
        ai_config = MagicMock()
        ai_config.industry_type = industry_type

    return doc, ai_config


class TestDielineByNameAnalyzer:
    """Tests for dieline detection by layer and spot color name matching."""

    @staticmethod
    def test_detects_dieline_layer() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, ai_config = _doc_with_layers(layer_names=["Dieline", "Artwork"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=ai_config)

        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "AI_DIE_001"
        assert f.severity == Severity.ADVISORY
        assert "Dieline" in f.message
        assert f.source == "ai"
        assert f.category == "dieline_detection"

    @staticmethod
    def test_detects_cut_contour_spot_color() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, ai_config = _doc_with_layers(spot_color_names=["CutContour"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=ai_config)

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DIE_001"
        assert "CutContour" in findings[0].message

    @staticmethod
    def test_detects_die_layer_case_insensitive() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(layer_names=["DIE LINE"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DIE_001"

    @staticmethod
    def test_detects_cut_layer() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(layer_names=["Cut"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1

    @staticmethod
    def test_detects_crease_layer() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(layer_names=["Crease Lines"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1

    @staticmethod
    def test_no_dieline_packaging_file_returns_delay() -> None:
        """Packaging file without dieline should get a DELAY severity warning."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, ai_config = _doc_with_layers(industry_type="packaging")
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf", ai_config=ai_config)

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DIE_002"
        assert findings[0].severity == Severity.WARNING
        assert "No die line detected" in findings[0].message

    @staticmethod
    def test_no_dieline_non_packaging_returns_advisory() -> None:
        """Non-packaging file without dieline should just get an advisory."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers()
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1
        assert findings[0].inspection_id == "AI_DIE_003"
        assert findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_detects_both_layer_and_spot_color() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(
            layer_names=["Die"],
            spot_color_names=["CutContour"],
        )
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1
        f = findings[0]
        assert "layers:" in f.message or "spot colors:" in f.message

    @staticmethod
    def test_deduplicates_by_name() -> None:
        """Same name in layers and spot colors should appear only once."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(
            layer_names=["CutContour"],
            spot_color_names=["CutContour"],
        )
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        assert len(findings) == 1

    @staticmethod
    def test_analyzer_metadata() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        analyzer = DielineByNameAnalyzer()
        assert analyzer.category == "dieline_detection"
        assert analyzer.feature_slug == "dieline_by_name"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1

    @staticmethod
    def test_findings_source_and_category() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc, _ = _doc_with_layers(layer_names=["Dieline"])
        analyzer = DielineByNameAnalyzer()
        findings = analyzer.analyze(doc, [], b"fake_pdf")

        for f in findings:
            assert f.source == "ai"
            assert f.category == "dieline_detection"
