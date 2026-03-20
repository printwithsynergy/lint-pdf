"""Tests for AnnotationAnalyzer — GRD_ANNOT_001-005."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.annotation import AnnotationAnalyzer
from grounded.analyzers.finding import Severity
from grounded.semantic.model import (
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
    """Test GRD_ANNOT_001: printable annotation inside trim area."""

    def test_printable_in_trim_delay(self) -> None:
        """Printable FreeText annotation inside trim triggers GRD_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x04,  # Print flag
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "GRD_ANNOT_001"]
        assert len(pa) == 1
        assert pa[0].severity == Severity.SQUALL

    def test_printable_outside_trim_no_finding(self) -> None:
        """Printable annotation outside trim does not trigger GRD_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(1, 1, 10, 10),  # Outside trim_box(20,20,592,772)
            flags=0x04,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "GRD_ANNOT_001"]
        assert len(pa) == 0

    def test_non_printable_no_finding(self) -> None:
        """Non-printable annotation does not trigger GRD_ANNOT_001."""
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,  # No print flag
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        analyzer = AnnotationAnalyzer()
        findings = analyzer.analyze(doc, [])
        pa = [f for f in findings if f.inspection_id == "GRD_ANNOT_001"]
        assert len(pa) == 0

    def test_printable_details(self) -> None:
        annot = PdfAnnotation(
            subtype="FreeText",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x04,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        pa = next((f for f in findings if f.inspection_id == "GRD_ANNOT_001"), None)
        assert pa is not None
        assert pa.details["subtype"] == "FreeText"
        assert pa.details["flags"] == 0x04


class TestMultimediaAnnotation:
    """Test GRD_ANNOT_002: multimedia annotation detection."""

    def test_sound_annotation(self) -> None:
        annot = PdfAnnotation(subtype="Sound", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "GRD_ANNOT_002"]
        assert len(mm) == 1
        assert mm[0].severity == Severity.AGROUND

    def test_movie_annotation(self) -> None:
        annot = PdfAnnotation(subtype="Movie", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "GRD_ANNOT_002"]
        assert len(mm) == 1

    def test_richmedia_annotation(self) -> None:
        annot = PdfAnnotation(subtype="RichMedia", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "GRD_ANNOT_002"]
        assert len(mm) == 1

    def test_3d_annotation(self) -> None:
        annot = PdfAnnotation(subtype="3D", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "GRD_ANNOT_002"]
        assert len(mm) == 1

    def test_text_annotation_not_multimedia(self) -> None:
        annot = PdfAnnotation(subtype="Text", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        mm = [f for f in findings if f.inspection_id == "GRD_ANNOT_002"]
        assert len(mm) == 0


class TestLinkAnnotation:
    """Test GRD_ANNOT_003: link annotation detection."""

    def test_link_advisory(self) -> None:
        annot = PdfAnnotation(subtype="Link", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        lnk = [f for f in findings if f.inspection_id == "GRD_ANNOT_003"]
        assert len(lnk) == 1
        assert lnk[0].severity == Severity.ADVISORY

    def test_non_link_no_finding(self) -> None:
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        lnk = [f for f in findings if f.inspection_id == "GRD_ANNOT_003"]
        assert len(lnk) == 0


class TestStampAnnotation:
    """Test GRD_ANNOT_004: stamp annotation detection."""

    def test_stamp_advisory(self) -> None:
        annot = PdfAnnotation(
            subtype="Stamp",
            rect=PdfBox(100, 100, 200, 200),
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        stp = [f for f in findings if f.inspection_id == "GRD_ANNOT_004"]
        assert len(stp) == 1
        assert stp[0].severity == Severity.ADVISORY

    def test_non_stamp_no_finding(self) -> None:
        annot = PdfAnnotation(subtype="Link", page_num=1)
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        stp = [f for f in findings if f.inspection_id == "GRD_ANNOT_004"]
        assert len(stp) == 0


class TestNonPrintingAnnotation:
    """Test GRD_ANNOT_005: non-printing annotation in trim area."""

    def test_non_printing_in_trim_advisory(self) -> None:
        """Non-printing, non-hidden Text annotation in trim triggers GRD_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,  # Not printable, not hidden
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "GRD_ANNOT_005"]
        assert len(np_f) == 1
        assert np_f[0].severity == Severity.ADVISORY

    def test_hidden_annotation_no_finding(self) -> None:
        """Hidden annotation does not trigger GRD_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x02,  # Hidden
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "GRD_ANNOT_005"]
        assert len(np_f) == 0

    def test_link_excluded(self) -> None:
        """Non-printing Link annotation does not trigger GRD_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Link",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "GRD_ANNOT_005"]
        assert len(np_f) == 0

    def test_popup_excluded(self) -> None:
        """Non-printing Popup annotation does not trigger GRD_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Popup",
            rect=PdfBox(100, 100, 200, 200),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "GRD_ANNOT_005"]
        assert len(np_f) == 0

    def test_outside_trim_no_finding(self) -> None:
        """Non-printing annotation outside trim does not trigger GRD_ANNOT_005."""
        annot = PdfAnnotation(
            subtype="Text",
            rect=PdfBox(1, 1, 10, 10),
            flags=0x00,
            page_num=1,
        )
        doc = _make_document(annotations=[annot])
        findings = AnnotationAnalyzer().analyze(doc, [])
        np_f = [f for f in findings if f.inspection_id == "GRD_ANNOT_005"]
        assert len(np_f) == 0


class TestAnnotationNoAnnotations:
    """Test analyzer with no annotations."""

    def test_empty_annotations_no_findings(self) -> None:
        doc = _make_document(annotations=[])
        findings = AnnotationAnalyzer().analyze(doc, [])
        annot_ids = {f.inspection_id for f in findings if f.inspection_id.startswith("GRD_ANNOT_")}
        assert len(annot_ids) == 0
