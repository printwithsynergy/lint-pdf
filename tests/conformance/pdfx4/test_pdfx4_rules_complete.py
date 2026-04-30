"""Gap-coverage tests for the PDF/X-4 conformance suite.

The per-sub-validator tests in this directory already cover 83 of the 91
``PDFX4-NNN`` rules. This file (a) plugs the 8 gaps for rules whose triggers
weren't asserted anywhere else, and (b) asserts every fired rule is also
registered in ``siftpdf.reports.check_names.CHECK_NAMES`` so the catalog
generator can group it under the ``pdfx4`` category.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.conformance.pdfx4._boxes import validate_boxes
from siftpdf.conformance.pdfx4._metadata import validate_metadata
from siftpdf.reports.check_names import CHECK_NAMES
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage

if TYPE_CHECKING:
    from siftpdf.analyzers.finding import Finding

_VALID_XMP_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description
    xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"
    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    pdfxid:GTS_PDFXVersion="PDF/X-4"
    {extra}>{title}</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""


def _xmp(extra: str = "", title: bool = True) -> bytes:
    title_block = (
        '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">T</rdf:li></rdf:Alt></dc:title>'
        if title
        else ""
    )
    return _VALID_XMP_BASE.format(extra=extra, title=title_block).encode("utf-8")


def _doc(
    metadata_stream: bytes, info: dict | None = None, version: str = "1.7"
) -> SemanticDocument:
    return SemanticDocument(
        version=version,
        page_count=1,
        is_encrypted=False,
        info_dict=info or {},
        metadata_stream=metadata_stream,
        output_intents=[{"/S": "/GTS_PDFX", "/OutputConditionIdentifier": "FOGRA39"}],
        trailer={"/ID": ["a", "b"]},
        pages=[
            SemanticPage(
                page_num=1, media_box=PdfBox(0, 0, 612, 792), trim_box=PdfBox(0, 0, 612, 792)
            )
        ],
    )


def _ids(findings: list[Finding]) -> set[str]:
    return {f.inspection_id for f in findings}


# ── Metadata gap fills (007, 008, 010, 011, 012, 014, 015) ────────────────


class TestMetadataGaps:
    @staticmethod
    def test_007_no_pdfx_conformance() -> None:
        # GTS_PDFXVersion present but no GTS_PDFXConformance.
        xmp = _xmp(
            extra='pdf:PDFVersion="1.7" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"'
        )
        assert "PDFX4-007" in _ids(validate_metadata(_doc(xmp)))

    @staticmethod
    def test_008_pdf_version_mismatch() -> None:
        # XMP says 1.6, header says 1.7.
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.6" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"'
        )
        assert "PDFX4-008" in _ids(validate_metadata(_doc(xmp, version="1.7")))

    @staticmethod
    def test_010_no_modify_date() -> None:
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.7" xmp:CreateDate="2024-01-01T00:00:00Z"'
        )
        assert "PDFX4-010" in _ids(validate_metadata(_doc(xmp)))

    @staticmethod
    def test_011_no_dc_title() -> None:
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.7" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"',
            title=False,
        )
        assert "PDFX4-011" in _ids(validate_metadata(_doc(xmp)))

    @staticmethod
    def test_012_invalid_trapped() -> None:
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.7" pdf:Trapped="Yes" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"'
        )
        assert "PDFX4-012" in _ids(validate_metadata(_doc(xmp)))

    @staticmethod
    def test_014_creation_date_mismatch() -> None:
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.7" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"'
        )
        info = {"/CreationDate": "D:20990101000000"}
        assert "PDFX4-014" in _ids(validate_metadata(_doc(xmp, info=info)))

    @staticmethod
    def test_015_mod_date_mismatch() -> None:
        xmp = _xmp(
            extra='pdfxid:GTS_PDFXConformance="PDF/X-4" pdf:PDFVersion="1.7" xmp:CreateDate="2024-01-01T00:00:00Z" xmp:ModifyDate="2024-01-01T00:00:00Z"'
        )
        info = {"/ModDate": "D:20990101000000"}
        assert "PDFX4-015" in _ids(validate_metadata(_doc(xmp, info=info)))


# ── Boxes gap fill (054) ───────────────────────────────────────────────────


class TestBoxesGaps:
    @staticmethod
    def test_054_zero_dimensions_fires() -> None:
        # PdfBox's __post_init__ rejects degenerate boxes, so we forge one
        # with object.__setattr__ to mimic what the parser does when a
        # malformed page-box dictionary slips through.
        bad_trim = PdfBox(0, 0, 1, 1)
        object.__setattr__(bad_trim, "x1", 0)
        object.__setattr__(bad_trim, "y1", 0)
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            metadata_stream=b"<x/>",
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    trim_box=bad_trim,
                )
            ],
        )
        assert "PDFX4-054" in _ids(validate_boxes(doc))


# ── Registry parity ────────────────────────────────────────────────────────


class TestRegistry:
    """All PDFX4-NNN IDs that any sub-validator can fire must be registered
    in CHECK_NAMES, otherwise the catalog generator will leak them under
    the ``other`` category."""

    @staticmethod
    def test_all_pdfx4_ids_in_check_names() -> None:
        # Static list — kept in sync with the 91 IDs implemented under
        # conformance/pdfx4/. Update when adding new rules.
        expected = [f"PDFX4-{n:03d}" for n in range(1, 93) if n != 45]
        missing = [cid for cid in expected if cid not in CHECK_NAMES]
        assert not missing, f"Missing CHECK_NAMES entries: {missing}"

    @staticmethod
    def test_no_orphan_pdfx4_in_check_names() -> None:
        # Catch a stray PDFX4-NNN entry in CHECK_NAMES that no sub-validator
        # actually emits.
        registered = {k for k in CHECK_NAMES if k.startswith("PDFX4-")}
        expected = {f"PDFX4-{n:03d}" for n in range(1, 93) if n != 45}
        orphans = registered - expected
        assert not orphans, f"Orphan PDFX4 entries in CHECK_NAMES: {orphans}"
