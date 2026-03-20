"""Tests for MetadataAnalyzer — GRD_META_001-004."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.analyzers.metadata import MetadataAnalyzer
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(
    metadata_stream: bytes | None = None,
    info_dict: dict | None = None,
    version: str = "1.7",
) -> SemanticDocument:
    return SemanticDocument(
        version=version,
        page_count=1,
        is_encrypted=False,
        metadata_stream=metadata_stream,
        info_dict=info_dict or {},
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _xmp_packet(
    title: str = "",
    trapped: str = "",
    pdf_version: str = "",
) -> bytes:
    """Build a minimal XMP metadata packet."""
    parts = [
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>',
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
    ]
    desc_attrs = (
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:pdf="http://ns.adobe.com/pdf/1.3/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/"'
    )
    parts.append(f"<rdf:Description {desc_attrs}")
    if trapped:
        parts.append(f' pdf:Trapped="{trapped}"')
    if pdf_version:
        parts.append(f' pdf:PDFVersion="{pdf_version}"')
    parts.append(">")
    if title:
        parts.append(
            f"<dc:title><rdf:Alt><rdf:li xml:lang='x-default'>{title}</rdf:li></rdf:Alt></dc:title>"
        )
    parts.append("</rdf:Description></rdf:RDF></x:xmpmeta>")
    parts.append('<?xpacket end="w"?>')
    return "".join(parts).encode("utf-8")


class TestXMPMissing:
    """Test GRD_META_001: XMP metadata stream missing."""

    @staticmethod
    def test_no_metadata_delay() -> None:
        doc = _make_document(metadata_stream=None)
        findings = MetadataAnalyzer().analyze(doc, [])
        meta = [f for f in findings if f.inspection_id == "GRD_META_001"]
        assert len(meta) == 1
        assert meta[0].severity == Severity.SQUALL

    @staticmethod
    def test_with_metadata_no_finding() -> None:
        doc = _make_document(metadata_stream=_xmp_packet())
        findings = MetadataAnalyzer().analyze(doc, [])
        meta = [f for f in findings if f.inspection_id == "GRD_META_001"]
        assert len(meta) == 0

    @staticmethod
    def test_no_metadata_returns_early() -> None:
        """When XMP is missing, no other META findings are generated."""
        doc = _make_document(metadata_stream=None)
        findings = MetadataAnalyzer().analyze(doc, [])
        meta_findings = [f for f in findings if f.inspection_id.startswith("GRD_META_")]
        assert len(meta_findings) == 1
        assert meta_findings[0].inspection_id == "GRD_META_001"


class TestTitleInconsistency:
    """Test GRD_META_002: Info dict / XMP title mismatch."""

    @staticmethod
    def test_title_mismatch_advisory() -> None:
        doc = _make_document(
            metadata_stream=_xmp_packet(title="XMP Title"),
            info_dict={"/Title": "Info Title"},
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        title = [f for f in findings if f.inspection_id == "GRD_META_002"]
        assert len(title) == 1
        assert title[0].severity == Severity.ADVISORY
        assert "Info Title" in title[0].message
        assert "XMP Title" in title[0].message

    @staticmethod
    def test_matching_titles_no_finding() -> None:
        doc = _make_document(
            metadata_stream=_xmp_packet(title="My Document"),
            info_dict={"/Title": "My Document"},
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        title = [f for f in findings if f.inspection_id == "GRD_META_002"]
        assert len(title) == 0

    @staticmethod
    def test_empty_info_title_no_finding() -> None:
        """Empty Info title does not trigger mismatch."""
        doc = _make_document(
            metadata_stream=_xmp_packet(title="XMP Title"),
            info_dict={"/Title": ""},
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        title = [f for f in findings if f.inspection_id == "GRD_META_002"]
        assert len(title) == 0

    @staticmethod
    def test_empty_xmp_title_no_finding() -> None:
        """Empty XMP title does not trigger mismatch."""
        doc = _make_document(
            metadata_stream=_xmp_packet(title=""),
            info_dict={"/Title": "Info Title"},
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        title = [f for f in findings if f.inspection_id == "GRD_META_002"]
        assert len(title) == 0


class TestTrappedKey:
    """Test GRD_META_003: Trapped key missing or Unknown."""

    @staticmethod
    def test_trapped_missing_advisory() -> None:
        doc = _make_document(metadata_stream=_xmp_packet(trapped=""))
        findings = MetadataAnalyzer().analyze(doc, [])
        trapped = [f for f in findings if f.inspection_id == "GRD_META_003"]
        assert len(trapped) == 1
        assert trapped[0].severity == Severity.ADVISORY
        assert "missing" in trapped[0].message

    @staticmethod
    def test_trapped_unknown_advisory() -> None:
        doc = _make_document(metadata_stream=_xmp_packet(trapped="Unknown"))
        findings = MetadataAnalyzer().analyze(doc, [])
        trapped = [f for f in findings if f.inspection_id == "GRD_META_003"]
        assert len(trapped) == 1
        assert "Unknown" in trapped[0].message

    @staticmethod
    def test_trapped_true_no_finding() -> None:
        doc = _make_document(metadata_stream=_xmp_packet(trapped="True"))
        findings = MetadataAnalyzer().analyze(doc, [])
        trapped = [f for f in findings if f.inspection_id == "GRD_META_003"]
        assert len(trapped) == 0

    @staticmethod
    def test_trapped_false_no_finding() -> None:
        doc = _make_document(metadata_stream=_xmp_packet(trapped="False"))
        findings = MetadataAnalyzer().analyze(doc, [])
        trapped = [f for f in findings if f.inspection_id == "GRD_META_003"]
        assert len(trapped) == 0


class TestPDFVersionMismatch:
    """Test GRD_META_004: PDF version mismatch."""

    @staticmethod
    def test_version_mismatch_advisory() -> None:
        doc = _make_document(
            version="1.7",
            metadata_stream=_xmp_packet(pdf_version="2.0"),
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        ver = [f for f in findings if f.inspection_id == "GRD_META_004"]
        assert len(ver) == 1
        assert ver[0].severity == Severity.ADVISORY
        assert "1.7" in ver[0].message
        assert "2.0" in ver[0].message

    @staticmethod
    def test_matching_version_no_finding() -> None:
        doc = _make_document(
            version="1.7",
            metadata_stream=_xmp_packet(pdf_version="1.7"),
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        ver = [f for f in findings if f.inspection_id == "GRD_META_004"]
        assert len(ver) == 0

    @staticmethod
    def test_no_xmp_version_no_finding() -> None:
        """XMP without PDFVersion does not trigger GRD_META_004."""
        doc = _make_document(
            version="1.7",
            metadata_stream=_xmp_packet(pdf_version=""),
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        ver = [f for f in findings if f.inspection_id == "GRD_META_004"]
        assert len(ver) == 0

    @staticmethod
    def test_version_mismatch_details() -> None:
        doc = _make_document(
            version="1.5",
            metadata_stream=_xmp_packet(pdf_version="1.7"),
        )
        findings = MetadataAnalyzer().analyze(doc, [])
        ver = next((f for f in findings if f.inspection_id == "GRD_META_004"), None)
        assert ver is not None
        assert ver.details["header_version"] == "1.5"
        assert ver.details["xmp_version"] == "1.7"
