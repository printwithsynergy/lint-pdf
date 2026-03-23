"""Tests for FontAnalyzer — font embedding, subsetting, and encoding checks."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.analyzers.font import FontAnalyzer
from grounded.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


def _make_font(
    name: str = "F1",
    base_font: str = "TestFont",
    font_type: str = "Type1",
    embedded: bool = True,
    subset: bool = True,
    encoding: str | None = "WinAnsiEncoding",
    font_descriptor: dict | None = None,
    has_to_unicode: bool = False,
    cid_system_info: dict | None = None,
) -> PdfFont:
    """Helper to create PdfFont."""
    return PdfFont(
        name=name,
        base_font=base_font,
        font_type=font_type,
        embedded=embedded,
        subset=subset,
        encoding=encoding,
        font_descriptor=font_descriptor,
        has_to_unicode=has_to_unicode,
        cid_system_info=cid_system_info,
    )


def _make_doc_with_font(font: PdfFont) -> SemanticDocument:
    """Create a document with a single font."""
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                fonts={font.name: font},
            )
        ],
    )


class TestFontEmbedding:
    """Test GRD_FONT_001: font embedding checks."""

    @staticmethod
    def test_embedded_font_no_finding() -> None:
        font = _make_font(embedded=True)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        embed_findings = [f for f in findings if f.inspection_id == "GRD_FONT_001"]
        assert len(embed_findings) == 0

    @staticmethod
    def test_not_embedded_triggers_aground() -> None:
        font = _make_font(base_font="CustomFont", embedded=False)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        embed_findings = [f for f in findings if f.inspection_id == "GRD_FONT_001"]
        assert len(embed_findings) == 1
        assert embed_findings[0].severity == Severity.ERROR

    @staticmethod
    def test_standard_14_not_embedded_ok() -> None:
        """Standard 14 fonts are exempt from embedding requirement."""
        font = _make_font(base_font="Helvetica", embedded=False)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        embed_findings = [f for f in findings if f.inspection_id == "GRD_FONT_001"]
        assert len(embed_findings) == 0


class TestFontSubsetting:
    """Test GRD_FONT_002: subsetting checks."""

    @staticmethod
    def test_subsetted_font_no_finding() -> None:
        font = _make_font(embedded=True, subset=True)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        sub_findings = [f for f in findings if f.inspection_id == "GRD_FONT_002"]
        assert len(sub_findings) == 0

    @staticmethod
    def test_not_subsetted_advisory() -> None:
        font = _make_font(embedded=True, subset=False)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        sub_findings = [f for f in findings if f.inspection_id == "GRD_FONT_002"]
        assert len(sub_findings) == 1
        assert sub_findings[0].severity == Severity.ADVISORY


class TestStandard14:
    """Test GRD_FONT_003: Standard 14 font detection."""

    @staticmethod
    def test_standard_14_advisory() -> None:
        font = _make_font(base_font="Courier", embedded=False)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        std14_findings = [f for f in findings if f.inspection_id == "GRD_FONT_003"]
        assert len(std14_findings) == 1
        assert std14_findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_non_standard_14_no_finding() -> None:
        font = _make_font(base_font="MyCustomFont", embedded=True)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        std14_findings = [f for f in findings if f.inspection_id == "GRD_FONT_003"]
        assert len(std14_findings) == 0


class TestType3:
    """Test GRD_FONT_004: Type 3 font detection."""

    @staticmethod
    def test_type3_delay() -> None:
        font = _make_font(font_type="Type3", embedded=True)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        t3_findings = [f for f in findings if f.inspection_id == "GRD_FONT_004"]
        assert len(t3_findings) == 1
        assert t3_findings[0].severity == Severity.WARNING


class TestCIDFonts:
    """Test GRD_FONT_005 and GRD_FONT_006: CID font checks."""

    @staticmethod
    def test_cid_missing_tounicode() -> None:
        font = _make_font(
            font_type="CIDFontType0",
            has_to_unicode=False,
            cid_system_info={"Registry": "Adobe", "Ordering": "Identity"},
        )
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        cid_findings = [f for f in findings if f.inspection_id == "GRD_FONT_005"]
        assert len(cid_findings) == 1

    @staticmethod
    def test_cid_with_tounicode_ok() -> None:
        font = _make_font(
            font_type="CIDFontType2",
            has_to_unicode=True,
            cid_system_info={"Registry": "Adobe", "Ordering": "Identity"},
        )
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        cid_findings = [f for f in findings if f.inspection_id == "GRD_FONT_005"]
        assert len(cid_findings) == 0

    @staticmethod
    def test_cid_missing_system_info() -> None:
        font = _make_font(
            font_type="CIDFontType0",
            cid_system_info=None,
        )
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        sys_findings = [f for f in findings if f.inspection_id == "GRD_FONT_006"]
        assert len(sys_findings) == 1


class TestFontEncoding:
    """Test GRD_FONT_007: missing encoding."""

    @staticmethod
    def test_no_encoding_advisory() -> None:
        font = _make_font(encoding=None)
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        enc_findings = [f for f in findings if f.inspection_id == "GRD_FONT_007"]
        assert len(enc_findings) == 1
        assert enc_findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_with_encoding_ok() -> None:
        font = _make_font(encoding="WinAnsiEncoding")
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        enc_findings = [f for f in findings if f.inspection_id == "GRD_FONT_007"]
        assert len(enc_findings) == 0


class TestTrueTypeEmbedding:
    """Test GRD_FONT_008: TrueType not embedded."""

    @staticmethod
    def test_truetype_not_embedded_aground() -> None:
        font = _make_font(
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
        )
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(_make_doc_with_font(font), [])
        tt_findings = [f for f in findings if f.inspection_id == "GRD_FONT_008"]
        assert len(tt_findings) == 1
        assert tt_findings[0].severity == Severity.ERROR


class TestDeduplication:
    """Test that fonts appearing on multiple pages are only reported once."""

    @staticmethod
    def test_same_font_two_pages() -> None:
        font = _make_font(base_font="CustomFont", embedded=False)
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    fonts={"F1": font},
                ),
                SemanticPage(
                    page_num=2,
                    media_box=PdfBox(0, 0, 612, 792),
                    fonts={"F1": font},
                ),
            ],
        )
        analyzer = FontAnalyzer()
        findings = analyzer.analyze(doc, [])
        embed_findings = [f for f in findings if f.inspection_id == "GRD_FONT_001"]
        # Should only report once, not twice
        assert len(embed_findings) == 1
