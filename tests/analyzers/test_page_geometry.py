"""Tests for PageGeometryAnalyzer — box hierarchy, bleed distance, safety margins."""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.page_geometry import PageGeometryAnalyzer
from lintpdf.semantic.events import PathPaintingEvent, TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import (
    PdfAnnotation,
    PdfBox,
    PdfColorSpace,
    PdfFont,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)


def _make_document(
    media_box: PdfBox | None = None,
    crop_box: PdfBox | None = None,
    bleed_box: PdfBox | None = None,
    trim_box: PdfBox | None = None,
    art_box: PdfBox | None = None,
) -> SemanticDocument:
    """Create a document with specified boxes."""
    if media_box is None:
        media_box = PdfBox(0, 0, 612, 792)
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=media_box,
                crop_box=crop_box,
                bleed_box=bleed_box,
                trim_box=trim_box,
                art_box=art_box,
            )
        ],
    )


class TestBoxPresence:
    """Test LPDF_BOX_001: required boxes present."""

    @staticmethod
    def test_missing_trim_box() -> None:
        doc = _make_document(trim_box=None, bleed_box=PdfBox(5, 5, 607, 787))
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        box_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_001"]
        trim_missing = [f for f in box_findings if "TrimBox" in f.message]
        assert len(trim_missing) == 1
        assert trim_missing[0].severity == Severity.WARNING

    @staticmethod
    def test_missing_bleed_box() -> None:
        doc = _make_document(trim_box=PdfBox(20, 20, 592, 772), bleed_box=None)
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        box_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_001"]
        bleed_missing = [f for f in box_findings if "BleedBox" in f.message]
        assert len(bleed_missing) == 1

    @staticmethod
    def test_both_boxes_present() -> None:
        doc = _make_document(
            trim_box=PdfBox(20, 20, 592, 772),
            bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        box_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_001"]
        assert len(box_findings) == 0

    @staticmethod
    def test_both_missing() -> None:
        doc = _make_document(trim_box=None, bleed_box=None)
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        box_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_001"]
        assert len(box_findings) == 2


class TestBoxHierarchy:
    """Test LPDF_BOX_002: box containment hierarchy."""

    @staticmethod
    def test_valid_hierarchy() -> None:
        doc = _make_document(
            media_box=PdfBox(0, 0, 612, 792),
            crop_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
            trim_box=PdfBox(20, 20, 592, 772),
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        hierarchy_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_002"]
        assert len(hierarchy_findings) == 0

    @staticmethod
    def test_crop_outside_media() -> None:
        doc = _make_document(
            media_box=PdfBox(0, 0, 612, 792),
            crop_box=PdfBox(-10, -10, 622, 802),
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        hierarchy_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_002"]
        assert len(hierarchy_findings) == 1
        assert "CropBox" in hierarchy_findings[0].message

    @staticmethod
    def test_trim_outside_bleed() -> None:
        doc = _make_document(
            bleed_box=PdfBox(20, 20, 592, 772),
            trim_box=PdfBox(10, 10, 602, 782),
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        hierarchy_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_002"]
        trim_outside = [f for f in hierarchy_findings if "TrimBox" in f.message]
        assert len(trim_outside) == 1


class TestBleedDistance:
    """Test LPDF_BOX_003: adequate bleed distance."""

    @staticmethod
    def test_adequate_bleed() -> None:
        """3mm bleed (8.5pt) on all sides."""
        doc = _make_document(
            trim_box=PdfBox(20, 20, 592, 772),
            bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
        )
        analyzer = PageGeometryAnalyzer(min_bleed_pts=8.5)
        findings = analyzer.analyze(doc, [])
        bleed_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_003"]
        assert len(bleed_findings) == 0

    @staticmethod
    def test_inadequate_bleed() -> None:
        """Only 2pt bleed — below 8.5pt minimum."""
        doc = _make_document(
            trim_box=PdfBox(20, 20, 592, 772),
            bleed_box=PdfBox(18, 18, 594, 774),
        )
        analyzer = PageGeometryAnalyzer(min_bleed_pts=8.5)
        findings = analyzer.analyze(doc, [])
        bleed_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_003"]
        assert len(bleed_findings) == 1
        assert bleed_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_zero_bleed() -> None:
        """TrimBox equals BleedBox — zero bleed."""
        doc = _make_document(
            trim_box=PdfBox(20, 20, 592, 772),
            bleed_box=PdfBox(20, 20, 592, 772),
        )
        analyzer = PageGeometryAnalyzer(min_bleed_pts=8.5)
        findings = analyzer.analyze(doc, [])
        bleed_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_003"]
        assert len(bleed_findings) == 1

    @staticmethod
    def test_configurable_min_bleed() -> None:
        """Custom minimum bleed (5mm = ~14.17pt)."""
        doc = _make_document(
            trim_box=PdfBox(20, 20, 592, 772),
            bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),  # 8.5pt bleed
        )
        # 8.5pt is fine for 3mm requirement
        analyzer_3mm = PageGeometryAnalyzer(min_bleed_pts=8.5)
        assert (
            len([f for f in analyzer_3mm.analyze(doc, []) if f.inspection_id == "LPDF_BOX_003"])
            == 0
        )

        # 8.5pt is NOT fine for 5mm requirement (14.17pt)
        analyzer_5mm = PageGeometryAnalyzer(min_bleed_pts=14.17)
        assert (
            len([f for f in analyzer_5mm.analyze(doc, []) if f.inspection_id == "LPDF_BOX_003"])
            == 1
        )


class TestMultiplePages:
    """Test analyzer works across multiple pages."""

    @staticmethod
    def test_two_pages() -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                ),
                SemanticPage(
                    page_num=2,
                    media_box=PdfBox(0, 0, 612, 792),
                    # Missing both boxes
                ),
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        # Page 1: OK. Page 2: missing TrimBox + BleedBox
        box_findings = [f for f in findings if f.inspection_id == "LPDF_BOX_001"]
        assert len(box_findings) == 2
        assert all(f.page_num == 2 for f in box_findings)


class TestEmptyPage:
    """Test LPDF_BOX_004: empty page (no content stream)."""

    @staticmethod
    def test_empty_page_advisory() -> None:
        """Page with no content stream triggers LPDF_BOX_004."""
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"",
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 1
        assert empty[0].severity == Severity.ADVISORY
        assert empty[0].page_num == 1

    @staticmethod
    def test_page_with_content_no_finding() -> None:
        """Page with content stream does not trigger LPDF_BOX_004."""
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"BT /F1 12 Tf (Hello) Tj ET",
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 0

    @staticmethod
    def test_mixed_pages_only_empty_flagged() -> None:
        """Only pages without content trigger LPDF_BOX_004."""
        doc = SemanticDocument(
            version="1.7",
            page_count=3,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"BT (Hi) Tj ET",
                ),
                SemanticPage(
                    page_num=2,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"",
                ),
                SemanticPage(
                    page_num=3,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"q Q",
                ),
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 1
        assert empty[0].page_num == 2

    @staticmethod
    def test_codex_path_with_fonts_no_finding() -> None:
        """Codex path sets content_stream=b""; page with fonts must NOT trigger BOX_004."""
        font = PdfFont(
            name="F1", base_font="Helvetica", font_type="Type1", embedded=False, subset=False
        )
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    content_stream=b"",
                    fonts={"F1": font},
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 0

    @staticmethod
    def test_codex_path_with_images_no_finding() -> None:
        """Codex path sets content_stream=b""; page with images must NOT trigger BOX_004."""
        cs = PdfColorSpace(name="CS1", cs_type="DeviceCMYK", components=4)
        img = PdfImage(
            name="Im1", width=100, height=100, bits_per_component=8, color_space=cs, page_num=1
        )
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    content_stream=b"",
                    images=[img],
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 0

    @staticmethod
    def test_codex_path_with_annotations_no_finding() -> None:
        """Codex path sets content_stream=b""; page with annotations must NOT trigger BOX_004."""
        annot = PdfAnnotation(subtype="Widget", rect=PdfBox(10, 10, 200, 50), page_num=1)
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    content_stream=b"",
                    annotations=[annot],
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 0

    @staticmethod
    def test_codex_path_vector_only_no_finding() -> None:
        """Codex path: page with content_ops (vector paths) but no fonts/images must NOT trigger BOX_004."""
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    content_stream=b"",
                    resources={
                        "codex_analysis": {
                            "content_ops": [
                                {"op": "m", "operands": [0.0, 0.0]},
                                {"op": "l", "operands": [100.0, 100.0]},
                                {"op": "S", "operands": []},
                            ]
                        }
                    },
                )
            ],
        )
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, [])
        empty = [f for f in findings if f.inspection_id == "LPDF_BOX_004"]
        assert len(empty) == 0


class TestContentSafetyMargin:
    """Test LPDF_BOX_005: content within safety margin of trim edge."""

    @staticmethod
    def _make_doc_with_trim() -> SemanticDocument:
        return SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"BT ET",
                )
            ],
        )

    def test_content_in_safety_margin_flags(self) -> None:
        """Content bbox touching safety margin of trim triggers BOX_005."""
        doc = self._make_doc_with_trim()
        # bbox near left edge of trim (20), within 8.5pt margin => x0 < 28.5
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(21.0, 100.0, 50.0, 200.0),
            )
        ]
        analyzer = PageGeometryAnalyzer(safety_margin_pts=8.5)
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_005"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    def test_content_well_inside_trim_no_flag(self) -> None:
        """Content well inside trim doesn't trigger BOX_005."""
        doc = self._make_doc_with_trim()
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(100.0, 100.0, 500.0, 600.0),
            )
        ]
        analyzer = PageGeometryAnalyzer(safety_margin_pts=8.5)
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_005"]
        assert len(f) == 0

    def test_text_event_in_safety_margin(self) -> None:
        """TextRenderedEvent near trim edge triggers BOX_005."""
        doc = self._make_doc_with_trim()
        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=0,
                font_name="F1",
                font_size=12.0,
                ctm=TransformationMatrix.identity(),
                text_matrix=TransformationMatrix.identity(),
                rendering_mode=0,
                bbox=(585.0, 100.0, 591.0, 112.0),  # near right trim edge (592)
            )
        ]
        analyzer = PageGeometryAnalyzer(safety_margin_pts=8.5)
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_005"]
        assert len(f) == 1

    @staticmethod
    def test_no_trim_box_no_safety_check() -> None:
        """Without trim box, no safety margin check."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"BT ET",
                )
            ],
        )
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(1.0, 1.0, 10.0, 10.0),
            )
        ]
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_005"]
        assert len(f) == 0

    def test_event_without_bbox_skipped(self) -> None:
        """Events with no bbox are skipped."""
        doc = self._make_doc_with_trim()
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=None,
            )
        ]
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_005"]
        assert len(f) == 0


class TestContentBeyondBleed:
    """Test LPDF_BOX_006: content extends beyond bleed box."""

    @staticmethod
    def _make_doc_with_bleed() -> SemanticDocument:
        return SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    bleed_box=PdfBox(11.5, 11.5, 600.5, 780.5),
                    content_stream=b"BT ET",
                )
            ],
        )

    def test_content_beyond_bleed_flags(self) -> None:
        doc = self._make_doc_with_bleed()
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(5.0, 5.0, 50.0, 50.0),  # extends beyond bleed (11.5)
            )
        ]
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_006"]
        assert len(f) == 1
        assert f[0].severity == Severity.WARNING

    def test_content_within_bleed_no_flag(self) -> None:
        doc = self._make_doc_with_bleed()
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(12.0, 12.0, 600.0, 780.0),
            )
        ]
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_006"]
        assert len(f) == 0

    @staticmethod
    def test_no_bleed_box_no_check() -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=PdfBox(20, 20, 592, 772),
                    content_stream=b"BT ET",
                )
            ],
        )
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                bbox=(0.0, 0.0, 612.0, 792.0),
            )
        ]
        analyzer = PageGeometryAnalyzer()
        findings = analyzer.analyze(doc, events)
        f = [f for f in findings if f.inspection_id == "LPDF_BOX_006"]
        assert len(f) == 0
