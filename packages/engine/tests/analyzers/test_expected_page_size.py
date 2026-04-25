"""Tests for LPDF_BOX_010 — page size vs expected product dimensions (T1-STR04)."""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.page_geometry import PageGeometryAnalyzer
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage

# A4 portrait in points: 595.28 x 841.89, ≈ 210.0 x 297.0 mm.
A4_W_PT = 595.28
A4_H_PT = 841.89
A4_W_MM = 210.0
A4_H_MM = 297.0


def _make_doc(width_pts: float, height_pts: float, rotate: int = 0) -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, width_pts, height_pts),
                trim_box=PdfBox(0, 0, width_pts, height_pts),
                rotate=rotate,
            )
        ],
    )


class TestDisabled:
    @staticmethod
    def test_no_expected_dims_silent() -> None:
        """Both expected_page_*_mm fields absent → check silently no-ops."""
        analyzer = PageGeometryAnalyzer()
        doc = _make_doc(A4_W_PT, A4_H_PT)
        findings = analyzer._check_expected_page_size(doc)
        assert findings == []

    @staticmethod
    def test_only_width_set_silent() -> None:
        """Width set but height absent — ambiguous, silent."""
        analyzer = PageGeometryAnalyzer(expected_page_width_mm=A4_W_MM)
        doc = _make_doc(A4_W_PT, A4_H_PT)
        assert analyzer._check_expected_page_size(doc) == []

    @staticmethod
    def test_only_height_set_silent() -> None:
        analyzer = PageGeometryAnalyzer(expected_page_height_mm=A4_H_MM)
        doc = _make_doc(A4_W_PT, A4_H_PT)
        assert analyzer._check_expected_page_size(doc) == []


class TestWithinTolerance:
    @staticmethod
    def test_exact_match_silent() -> None:
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        doc = _make_doc(A4_W_PT, A4_H_PT)
        assert analyzer._check_expected_page_size(doc) == []

    @staticmethod
    def test_within_default_tolerance() -> None:
        """0.3mm diff < 0.5mm default tolerance → no finding."""
        # 0.3mm ≈ 0.85 pts
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        doc = _make_doc(A4_W_PT + 0.85, A4_H_PT)
        assert analyzer._check_expected_page_size(doc) == []

    @staticmethod
    def test_landscape_rotation_accepted() -> None:
        """A4 expected portrait, A4 given landscape → silent. Either orientation OK."""
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        doc = _make_doc(A4_H_PT, A4_W_PT)
        assert analyzer._check_expected_page_size(doc) == []


class TestOutOfRange:
    @staticmethod
    def test_too_small_fires() -> None:
        """210x250 given but 210x297 expected → fires."""
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        # 250mm ≈ 708.66 pts
        doc = _make_doc(A4_W_PT, 708.66)
        findings = analyzer._check_expected_page_size(doc)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_BOX_010"
        assert f.severity == Severity.WARNING
        assert f.details["expected_width_mm"] == A4_W_MM
        assert f.details["expected_height_mm"] == A4_H_MM
        assert abs(f.details["actual_width_mm"] - 210.0) < 0.01
        assert 249.9 < f.details["actual_height_mm"] < 250.1

    @staticmethod
    def test_way_out_fires() -> None:
        """A3 given, A4 expected → fires."""
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        # A3 ≈ 842 x 1190 pts
        doc = _make_doc(842.0, 1190.0)
        findings = analyzer._check_expected_page_size(doc)
        assert len(findings) == 1

    @staticmethod
    def test_tolerance_configurable() -> None:
        """Tight tolerance (0.1mm) should catch what 0.5mm didn't."""
        analyzer_loose = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        analyzer_tight = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM,
            expected_page_height_mm=A4_H_MM,
            expected_page_size_tolerance_mm=0.1,
        )
        # 0.3mm off — within loose, over tight
        doc = _make_doc(A4_W_PT + 0.85, A4_H_PT)
        assert analyzer_loose._check_expected_page_size(doc) == []
        findings = analyzer_tight._check_expected_page_size(doc)
        assert len(findings) == 1


class TestRotation:
    @staticmethod
    def test_rotated_page_uses_effective_dims() -> None:
        """Page with /Rotate 90 on a 210x297 media box should match
        (210, 297) expected — the rotation-swap is handled."""
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        doc = _make_doc(A4_W_PT, A4_H_PT, rotate=90)
        # After rotation, actual becomes (A4_H_MM, A4_W_MM) which is the
        # landscape orientation of A4. Check accepts either orientation.
        assert analyzer._check_expected_page_size(doc) == []


class TestAnalyzeIntegration:
    @staticmethod
    def test_analyze_routes_through_check() -> None:
        """Full analyze() call emits LPDF_BOX_010 when page size mismatches."""
        analyzer = PageGeometryAnalyzer(
            expected_page_width_mm=A4_W_MM, expected_page_height_mm=A4_H_MM
        )
        doc = _make_doc(100.0, 100.0)  # 35mm x 35mm — way off
        findings = analyzer.analyze(doc, events=[])
        box_010 = [f for f in findings if f.inspection_id == "LPDF_BOX_010"]
        assert len(box_010) == 1
