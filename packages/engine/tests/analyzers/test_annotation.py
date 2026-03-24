"""Tests for AnnotationAnalyzer — LPDF_ANNOT_001-005."""

from __future__ import annotations

from lintpdf.analyzers.annotation import AnnotationAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.model import (
    PdfAnnotation,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _make_document(
    annotations: list[PdfAnnotation] | None = None,
    trim_box: PdfBox | None = None,
) -> SemanticDocument:
    if trim_box is None:
        trim_box = PdfBox(20, 20, 592, 772)
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                trim_box=trim_box,
                annotations=annotations or [],
            )
        ],
    )


class TestPrintableAnnotationInTrim:
    """Test LPDF_ANNOT_001: printable annotation inside trim area."""

    @staticmethod
    def test_printable_in_trim_delay() -> None:
        """Printable FreeText annotation inside trim triggers LPDF_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x04,  # Print flag
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "LPDF_ANNOT_001"]
        assert len(pa) == 1
        assert pa[0].severity == Severity.WARNING

    @staticmethod
    def test_printable_outside_trim_no_finding() -> None:
        """Printable annotation outside trim does not trigger LPDF_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(1, 1, 10, 10),  # Outside trim_box(20,20,592,772)
            flags=0x04,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "LPDF_ANNOT_001"]
        assert len(pa) == 0

    @staticmethod
    def test_non_printable_no_finding() -> None:
        """Non-printable annotation does not trigger LPDF_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,  # No print flag
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "LPDF_ANNOT_001"]
        assert len(pa) == 0

    @staticmethod
    def test_printable_details() -> None:
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x04,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        pa = next((f for f in findings if f.inspection_id == "LPDF_ANNOT_001"), None)
        assert pa is not None
        assert pa.details["subtype"] == "FreeText"
        assert pa.details["flags"] == 0x04


class TestMultimediaAnnotation:
    """Test LPDF_ANNOT_002: multimedia annotation detection."""

    @staticmethod
    def test_sound_annotation() -> None:
        annot = PdfAnnotation(subtype="Sound", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "LPDF_ANNOT_002"]
        assert len(mm) == 1
        assert mm[0].severity == Severity.ERROR

    @staticmethod
    def test_movie_annotation() -> None:
        annot = PdfAnnotation(subtype="Movie", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "LPDF_ANNOT_002"]
        assert len(mm) == 1

    @staticmethod
    def test_richmedia_annotation() -> None:
        annot = PdfAnnotation(subtype="RichMedia", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "LPDF_ANNOT_002"]
        assert len(mm) == 1

    @staticmethod
    def test_3d_annotation() -> None:
        annot = PdfAnnotation(subtype="3D", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "LPDF_ANNOT_002"]
        assert len(mm) == 1

    @staticmethod
    def test_text_annotation_not_multimedia() -> None:
        annot = PdfAnnotation(subtype="Text", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "LPDF_ANNOT_002"]
        assert len(mm) == 0


class TestLinkAnnotation:
    """Test LPDF_ANNOT_003: link annotation detection."""

    @staticmethod
    def test_link_advisory() -> None:
        annot = PdfAnnotation(subtype="Link", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        lnk = [f for f in findings if f.inspection_id == "LPDF_ANNOT_003"]
        assert len(lnk) == 1
        assert lnk[0].severity == Severity.ADVISORY

    @staticmethod
    def test_non_link_no_finding() -> None:
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        lnk = [f for f in findings if f.inspection_id == "LPDF_ANNOT_003"]
        assert len(lnk) == 0


class TestStampAnnotation:
    """Test LPDF_ANNOT_004: stamp annotation detection."""

    @staticmethod
    def test_stamp_advisory() -> None:
        annot = PdfAnnotation(
            subtype="Stamp",
            rect=PdfBox(100, 100, 200, 200),
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        stp = [f for f in findings if f.inspection_id == "LPDF_ANNOT_004"]
        assert len(stp) == 1
        assert stp[0].severity == Severity.ADVISORY

    @staticmethod
    def test_non_stamp_no_finding() -> None:
        annot = PdfAnnotation(subtype="Link", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        stp = [f for f in findings if f.inspection_id == "LPDF_ANNOT_004"]
        assert len(stp) == 0


class TestNonPrintingAnnotation:
    """Test LPDF_ANNOT_005: non-printing annotation in trim area."""

    @staticmethod
    def test_non_printing_in_trim_advisory() -> None:
        """Non-printing, non-hidden Text annotation in trim triggers LPDF_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,  # Not printable, not hidden
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "LPDF_ANNOT_005"]
        assert len(np_f) == 1
        assert np_f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_hidden_annotation_no_finding() -> None:
        """Hidden annotation does not trigger LPDF_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x02,  # Hidden
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "LPDF_ANNOT_005"]
        assert len(np_f) == 0

    @staticmethod
    def test_link_excluded() -> None:
        """Non-printing Link annotation does not trigger LPDF_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Link",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "LPDF_ANNOT_005"]
        assert len(np_f) == 0

    @staticmethod
    def test_popup_excluded() -> None:
        """Non-printing Popup annotation does not trigger LPDF_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Popup",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "LPDF_ANNOT_005"]
        assert len(np_f) == 0

    @staticmethod
    def test_outside_trim_no_finding() -> None:
        """Non-printing annotation outside trim does not trigger LPDF_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(1, 1, 10, 10),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "LPDF_ANNOT_005"]
        assert len(np_f) == 0


class TestAnnotationNoAnnotations:
    """Test analyzer with no annotations."""

    @staticmethod
    def test_empty_annotations_no_findings() -> None:
        doc = _make_document(annotations=[])
        findings = AnnotationAnalyzer().analyze(doc, [])
        annot_ids = {f.inspection_id for f in findings if f.inspection_id.startswith("LPDF_ANNOT_")}
        assert len(annot_ids) == 0
