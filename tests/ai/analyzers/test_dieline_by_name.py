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


# ---------------------------------------------------------------------------
# Text-indicator dieline detection (added 2026-04-28 after audit)
# ---------------------------------------------------------------------------


def _doc_with_text(text: str) -> MagicMock:
    """Build a doc whose single page carries arbitrary content stream
    text — used to exercise the tear/perf indicator path."""
    doc = MagicMock()
    doc.page_count = 1
    doc.version = "1.7"
    doc.is_encrypted = False
    doc.catalog = {}
    page = MagicMock()
    page.page_num = 1
    page.color_spaces = {}
    page.resources = {}
    page.content_stream = text.encode("latin-1")
    doc.pages = [page]
    return doc


class TestTextIndicatorDielineDetection:
    """``AI_DIE_001`` should fire on tear/perf/fold callouts even
    when no named dieline spot or layer is declared. Inverse:
    ``AI_DIE_002`` should NOT fire."""

    @staticmethod
    def test_tear_across_english_detected() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("(TEAR ACROSS) Tj artwork content")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        assert any(f.inspection_id == "AI_DIE_001" for f in findings)
        assert not any(f.inspection_id == "AI_DIE_002" for f in findings)

    @staticmethod
    def test_dechirer_ici_french_detected() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("(DÉCHIRER ICI) Tj")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        assert any(f.inspection_id == "AI_DIE_001" for f in findings)

    @staticmethod
    def test_tear_here_detected() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("(TEAR HERE) Tj")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        assert any(f.inspection_id == "AI_DIE_001" for f in findings)

    @staticmethod
    def test_open_here_detected() -> None:
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("(OPEN HERE) Tj")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        assert any(f.inspection_id == "AI_DIE_001" for f in findings)

    @staticmethod
    def test_clean_artwork_no_dieline_finding() -> None:
        """No tear/perf indicators and no spot/layer → AI_DIE_002 still fires
        (or AI_DIE_005 for non-packaging — depends on industry detection)."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("Plain marketing copy with no dieline indicators.")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        # Either AI_DIE_002 (packaging) or AI_DIE_005 (non-packaging) is
        # acceptable; the key is that AI_DIE_001 does NOT fire.
        assert not any(f.inspection_id == "AI_DIE_001" for f in findings)

    @staticmethod
    def test_marketing_use_of_word_tear_does_not_fire() -> None:
        """``Tear-jerker special offer`` should NOT trigger — pattern
        requires the literal callout phrase (``TEAR ACROSS`` etc.)."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        doc = _doc_with_text("(Tear-jerker special offer inside) Tj")
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        assert not any(f.inspection_id == "AI_DIE_001" for f in findings)

    @staticmethod
    def test_combined_spot_and_text_indicator_dedupes_naturally() -> None:
        """A doc with both a /Cutting spot AND a TEAR ACROSS callout
        should still fire AI_DIE_001 once (the pattern emits one finding
        regardless of how many sources triggered)."""
        from lintpdf.ai.analyzers.dieline_detection.dieline_by_name import (
            DielineByNameAnalyzer,
        )

        # Build a doc with both a Cutting spot and a TEAR callout.
        doc, _ = _doc_with_layers(layer_names=[], spot_color_names=["Cutting"])
        doc.pages[0].content_stream = b"(TEAR ACROSS) Tj"
        findings = DielineByNameAnalyzer().analyze(doc, [], b"")
        die_001 = [f for f in findings if f.inspection_id == "AI_DIE_001"]
        assert len(die_001) == 1
        # Both sources should appear in the message.
        msg = die_001[0].message
        assert "Cutting" in msg
        assert "TEAR" in msg.upper()
