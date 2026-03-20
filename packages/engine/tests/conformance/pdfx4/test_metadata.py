"""Tests for PDF/X-4 metadata checks (PDFX4-005-015)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._metadata import validate_metadata
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage

_VALID_XMP = b"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description
    xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"
    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    pdfxid:GTS_PDFXVersion="PDF/X-4"
    pdfxid:GTS_PDFXConformance="PDF/X-4"
    pdf:PDFVersion="1.7"
    pdf:Trapped="False"
    xmp:CreateDate="2024-01-01T00:00:00Z"
    xmp:ModifyDate="2024-01-01T00:00:00Z">
    <dc:title><rdf:Alt><rdf:li xml:lang="x-default">Test Doc</rdf:li></rdf:Alt></dc:title>
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""


def _doc(
    metadata_stream: bytes | None = _VALID_XMP,
    info_dict: dict[str, Any] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        metadata_stream=metadata_stream,
        info_dict=info_dict or {"/Title": "Test Doc"},
    )


class TestXmpPresence:
    def test_missing_xmp_aground(self) -> None:
        f = validate_metadata(_doc(metadata_stream=None))
        ids = [x for x in f if x.inspection_id == "PDFX4-005"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_valid_xmp_ok(self) -> None:
        f = validate_metadata(_doc())
        assert not [x for x in f if x.inspection_id == "PDFX4-005"]


class TestPdfxVersion:
    def test_missing_pdfx_version(self) -> None:
        xmp = b"""<?xml version="1.0"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmp:CreateDate="2024-01-01T00:00:00Z"
    xmp:ModifyDate="2024-01-01T00:00:00Z">
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""
        f = validate_metadata(_doc(metadata_stream=xmp))
        ids = [x for x in f if x.inspection_id == "PDFX4-006"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_wrong_pdfx_version(self) -> None:
        xmp = b"""<?xml version="1.0"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"
    pdfxid:GTS_PDFXVersion="PDF/X-1a:2003">
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""
        f = validate_metadata(_doc(metadata_stream=xmp))
        ids = [x for x in f if x.inspection_id == "PDFX4-006"]
        assert len(ids) == 1

    def test_valid_pdfx_version(self) -> None:
        f = validate_metadata(_doc())
        assert not [x for x in f if x.inspection_id == "PDFX4-006"]


class TestDates:
    def test_missing_create_date(self) -> None:
        xmp = b"""<?xml version="1.0"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    pdfxid:GTS_PDFXVersion="PDF/X-4"
    xmp:ModifyDate="2024-01-01T00:00:00Z">
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""
        f = validate_metadata(_doc(metadata_stream=xmp))
        ids = [x for x in f if x.inspection_id == "PDFX4-009"]
        assert len(ids) == 1


class TestTitleConsistency:
    def test_title_mismatch(self) -> None:
        f = validate_metadata(_doc(info_dict={"/Title": "Different Title"}))
        ids = [x for x in f if x.inspection_id == "PDFX4-013"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    def test_title_match(self) -> None:
        f = validate_metadata(_doc(info_dict={"/Title": "Test Doc"}))
        assert not [x for x in f if x.inspection_id == "PDFX4-013"]
