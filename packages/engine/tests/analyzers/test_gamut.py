"""Tests for GamutAnalyzer — CMYK and RGB gamut boundary checking."""

import pytest

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.gamut_analyzer import (
    GamutAnalyzer,
    cmyk_to_lab,
    srgb_to_lab,
)
from lintpdf.profiles.icc.gamut_boundary import GamutBoundary, load_gamut_boundary
from lintpdf.profiles.icc.profile_manager import get_gamut_boundary
from lintpdf.semantic.events import ColorChangedEvent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_doc(output_intents=None):
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[page],
        output_intents=output_intents or [],
    )


def _make_color_event(cs, values, page=1, stroking=False):
    return ColorChangedEvent(
        operator="sc",
        page_num=page,
        operator_index=0,
        stroking=stroking,
        color_space=cs,
        color_values=tuple(values),
    )


class TestSrgbToLab:
    def test_white(self):
        lab = srgb_to_lab(1.0, 1.0, 1.0)
        assert abs(lab[0] - 100.0) < 1.0  # L* ≈ 100
        assert abs(lab[1]) < 1.0  # a* ≈ 0
        assert abs(lab[2]) < 1.0  # b* ≈ 0

    def test_black(self):
        lab = srgb_to_lab(0.0, 0.0, 0.0)
        assert abs(lab[0]) < 1.0  # L* ≈ 0

    def test_red(self):
        lab = srgb_to_lab(1.0, 0.0, 0.0)
        assert lab[0] > 40  # Red has mid-range L*
        assert lab[1] > 50  # Positive a* (red)


class TestCmykToLab:
    def test_pure_cyan_naive(self):
        """Naive conversion of pure cyan should give a reasonable Lab value."""
        lab = cmyk_to_lab(1.0, 0.0, 0.0, 0.0)
        assert lab[1] < 0  # a* should be negative (green direction)
        assert lab[2] < 0  # b* should be negative (blue direction)

    def test_pure_black_naive(self):
        """K=100% should be near L*=0."""
        lab = cmyk_to_lab(0.0, 0.0, 0.0, 1.0)
        assert lab[0] < 5.0

    def test_white_paper_naive(self):
        """All zeros should be near paper white."""
        lab = cmyk_to_lab(0.0, 0.0, 0.0, 0.0)
        assert lab[0] > 95.0

    def test_with_none_profile_falls_back(self):
        """Passing None for profile bytes should use naive conversion."""
        lab = cmyk_to_lab(0.5, 0.3, 0.2, 0.1, icc_profile_bytes=None)
        assert isinstance(lab, tuple)
        assert len(lab) == 3


class TestGamutBoundaryLoading:
    def test_load_fogra39(self):
        boundary = get_gamut_boundary("fogra39_coated")
        assert boundary is not None
        assert boundary.condition_name == "FOGRA39 Coated Offset"
        assert boundary.volume > 0
        assert len(boundary.vertices) > 0
        assert len(boundary.equations) > 0

    def test_load_srgb(self):
        boundary = get_gamut_boundary("srgb")
        assert boundary is not None
        assert boundary.volume > 500000  # sRGB has large volume

    def test_load_nonexistent(self):
        boundary = get_gamut_boundary("nonexistent_condition")
        assert boundary is None

    def test_in_gamut_midtone(self):
        """A midtone neutral should be in gamut for coated offset."""
        boundary = get_gamut_boundary("fogra39_coated")
        assert boundary is not None
        assert boundary.is_in_gamut((50.0, 0.0, 0.0))


class TestGamutAnalyzerRgb:
    def test_no_target_condition(self):
        analyzer = GamutAnalyzer(target_condition="")
        doc = _make_doc()
        events = [_make_color_event("DeviceRGB", [1.0, 0.0, 0.0])]
        findings = analyzer.analyze(doc, events)
        advisory = [
            f
            for f in findings
            if f.inspection_id == "LPDF_GAMUT_001" and f.severity == Severity.ADVISORY
        ]
        assert len(advisory) >= 1

    def test_rgb_in_gamut(self):
        """A neutral gray should be in gamut for any CMYK condition."""
        analyzer = GamutAnalyzer(target_condition="fogra39_coated")
        doc = _make_doc()
        events = [_make_color_event("DeviceRGB", [0.5, 0.5, 0.5])]
        findings = analyzer.analyze(doc, events)
        warnings = [
            f
            for f in findings
            if f.inspection_id == "LPDF_GAMUT_001" and f.severity == Severity.WARNING
        ]
        assert len(warnings) == 0


class TestGamutAnalyzerCmyk:
    def test_cmyk_neutral_in_gamut(self):
        """Neutral CMYK should be in gamut for matching condition."""
        analyzer = GamutAnalyzer(target_condition="fogra39_coated")
        doc = _make_doc()
        events = [_make_color_event("DeviceCMYK", [0.0, 0.0, 0.0, 0.5])]
        findings = analyzer.analyze(doc, events)
        squall_001 = [
            f
            for f in findings
            if f.inspection_id == "LPDF_GAMUT_001" and f.severity == Severity.WARNING
        ]
        # A 50% gray should be in gamut
        assert len(squall_001) == 0

    def test_cmyk_uses_naive_without_profile(self):
        """Without ICC profile bytes, conversion method should be 'naive'."""
        analyzer = GamutAnalyzer(target_condition="fogra39_coated")
        doc = _make_doc()
        # Use a saturated color more likely to produce findings
        events = [_make_color_event("DeviceCMYK", [1.0, 1.0, 0.0, 0.0])]
        findings = analyzer.analyze(doc, events)
        for f in findings:
            if f.inspection_id == "LPDF_GAMUT_001" and f.details.get("conversion_method"):
                assert f.details["conversion_method"] == "naive"

    def test_summary_includes_cmyk(self):
        """LPDF_GAMUT_003 summary should include CMYK counts."""
        analyzer = GamutAnalyzer(target_condition="fogra39_coated")
        doc = _make_doc()
        events = [
            _make_color_event("DeviceCMYK", [0.5, 0.3, 0.2, 0.1]),
            _make_color_event("DeviceRGB", [0.5, 0.5, 0.5]),
        ]
        findings = analyzer.analyze(doc, events)
        summary = [f for f in findings if f.inspection_id == "LPDF_GAMUT_003"]
        assert len(summary) == 1
        assert summary[0].details["total_cmyk_colors"] == 1
        assert summary[0].details["total_rgb_colors"] == 1
        assert "out_of_gamut_cmyk" in summary[0].details
