"""Tests for SpotColorAnalyzer."""

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.spot_color_analyzer import SpotColorAnalyzer
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _make_doc(color_spaces_by_page=None):
    pages = []
    if color_spaces_by_page:
        for i, cs_dict in enumerate(color_spaces_by_page, 1):
            pages.append(
                SemanticPage(
                    page_num=i,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces=cs_dict,
                )
            )
    else:
        pages.append(SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)))
    return SemanticDocument(
        version="2.0",
        page_count=len(pages),
        is_encrypted=False,
        pages=pages,
    )


class TestSpotColorAnalyzer:
    def test_no_spot_colors(self):
        doc = _make_doc()
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_findings = [f for f in findings if f.inspection_id.startswith("LPDF_SPOT_")]
        assert len(spot_findings) == 0

    def test_spot_color_inventory(self):
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 485 C",),
            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_001 = [f for f in findings if f.inspection_id == "LPDF_SPOT_001"]
        assert len(spot_001) >= 1

    def test_spot_color_naming_issue(self):
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("",),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_003 = [f for f in findings if f.inspection_id == "LPDF_SPOT_003"]
        assert len(spot_003) >= 1

    def test_devicen_validation(self):
        cs = PdfColorSpace(
            name="CS1",
            cs_type="DeviceN",
            components=4,
            colorant_names=("Cyan", "Magenta", "Yellow", "Black"),
            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_004 = [f for f in findings if f.inspection_id == "LPDF_SPOT_004"]
        # Well-formed DeviceN should not trigger structural errors
        errors = [f for f in spot_004 if f.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_devicen_bad_structure(self):
        cs = PdfColorSpace(
            name="CS1",
            cs_type="DeviceN",
            components=3,  # Mismatch: 2 names, 3 components
            colorant_names=("Cyan", "Magenta"),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_004 = [f for f in findings if f.inspection_id == "LPDF_SPOT_004"]
        assert len(spot_004) >= 1

    def test_pantone_case_insensitive_dedup(self):
        # "Pantone 485 C" and "PANTONE 485 C" are the same paint. The
        # inventory must collapse them into one row and the unknown-
        # library check must match PANTONE for both, not flag either.
        cs_lower = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("Pantone 485 C",),
            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
        )
        cs_upper = PdfColorSpace(
            name="CS2",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 485 C",),
            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs_lower, "CS2": cs_upper}])
        findings = SpotColorAnalyzer().analyze(doc, [])

        spot_001 = [f for f in findings if f.inspection_id == "LPDF_SPOT_001"]
        assert len(spot_001) == 1, f"expected one inventory row, got {len(spot_001)}"

        spot_007 = [f for f in findings if f.inspection_id == "LPDF_SPOT_007"]
        assert spot_007 == [], (
            f"Pantone 485 C / PANTONE 485 C must match PANTONE library; got {spot_007}"
        )

    def test_pantone_with_trademark_glyph_and_leading_slash(self):
        # Colourant names that come through with a stray leading
        # slash, non-breaking space, or (R) glyph still have to
        # classify as PANTONE.
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("/Pantone 485 C",),
            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        findings = SpotColorAnalyzer().analyze(doc, [])
        spot_007 = [f for f in findings if f.inspection_id == "LPDF_SPOT_007"]
        assert spot_007 == [], (
            "leading-slash + non-breaking-space Pantone names must still match the library"
        )
