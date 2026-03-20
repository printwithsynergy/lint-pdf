"""Integration test for PdfX4Validator end-to-end."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4 import PdfX4Validator
from grounded.semantic.model import PdfAnnotation, PdfBox, SemanticDocument, SemanticPage

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


def _compliant_doc() -> SemanticDocument:
    """Build a minimally compliant PDF/X-4 document."""
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        info_dict={"/Title": "Test Doc"},
        metadata_stream=_VALID_XMP,
        output_intents=[
            {
                "/S": "/GTS_PDFX",
                "/OutputConditionIdentifier": "FOGRA39",
                "/RegistryName": "http://www.color.org",
                "/Info": "FOGRA39 coated",
            }
        ],
        trailer={"/ID": ["abc", "def"]},
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                trim_box=PdfBox(10, 10, 602, 782),
            )
        ],
    )


class TestPdfX4ValidatorIntegration:
    def test_compliant_doc_minimal_findings(self) -> None:
        validator = PdfX4Validator()
        findings = validator.validate(_compliant_doc(), [])
        # A well-formed doc should have no AGROUND findings
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert len(aground) == 0

    def test_encrypted_doc_aground(self) -> None:
        doc = _compliant_doc()
        doc.is_encrypted = True
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-063" for f in aground)

    def test_missing_xmp_aground(self) -> None:
        doc = _compliant_doc()
        doc.metadata_stream = None
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-005" for f in aground)

    def test_old_version_aground(self) -> None:
        doc = _compliant_doc()
        doc.version = "1.4"
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-001" for f in aground)

    def test_prohibited_annotation_aground(self) -> None:
        doc = _compliant_doc()
        doc.pages[0].annotations = [PdfAnnotation(subtype="Sound", page_num=1)]
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-057" for f in aground)

    def test_no_output_intent_aground(self) -> None:
        doc = _compliant_doc()
        doc.output_intents = []
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-016" for f in aground)

    def test_no_trim_no_art_aground(self) -> None:
        doc = _compliant_doc()
        doc.pages[0].trim_box = None
        doc.pages[0].art_box = None
        validator = PdfX4Validator()
        findings = validator.validate(doc, [])
        aground = [f for f in findings if f.severity == Severity.AGROUND]
        assert any(f.inspection_id == "PDFX4-050" for f in aground)

    def test_all_check_ids_prefixed(self) -> None:
        validator = PdfX4Validator()
        findings = validator.validate(_compliant_doc(), [])
        for f in findings:
            assert f.inspection_id.startswith("PDFX4-"), f"Unexpected prefix: {f.inspection_id}"
