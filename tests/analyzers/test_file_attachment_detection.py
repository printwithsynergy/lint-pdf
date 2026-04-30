"""Tests for T1-CMP06 / LPDF_STRUCT_004 — /FileAttachment annotation detection.

LPDF_STRUCT_004 historically fired only on /Names /EmbeddedFiles at the
catalog level. This test suite covers the added path: /FileAttachment
annotations on any page, which is the second way PDFs embed files per
ISO 32000-2 §12.5.6.15.
"""

from __future__ import annotations

from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.structure import StructureAnalyzer
from siftpdf.semantic.model import (
    PdfAnnotation,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _doc_with_annotations(*subtypes: str) -> SemanticDocument:
    annots = [
        PdfAnnotation(
            subtype=st,
            rect=PdfBox(0, 0, 50, 50),
            flags=4,
            contents="",
            page_num=1,
        )
        for st in subtypes
    ]
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                annotations=annots,
            )
        ],
    )


class TestFileAttachmentAnnotation:
    @staticmethod
    def test_single_file_attachment_fires() -> None:
        doc = _doc_with_annotations("/FileAttachment")
        findings = StructureAnalyzer().analyze(doc, events=[])
        struct_004 = [f for f in findings if f.inspection_id == "LPDF_STRUCT_004"]
        assert len(struct_004) == 1
        f = struct_004[0]
        assert f.severity == Severity.WARNING
        assert f.details["source"] == "file_attachment_annotation"
        assert f.details["attachment_count"] == 1

    @staticmethod
    def test_multiple_attachments_single_finding() -> None:
        """Multiple attachments on one page → one finding with count details."""
        doc = _doc_with_annotations("/FileAttachment", "/FileAttachment", "/FileAttachment")
        findings = StructureAnalyzer().analyze(doc, events=[])
        struct_004 = [f for f in findings if f.inspection_id == "LPDF_STRUCT_004"]
        assert len(struct_004) == 1
        assert struct_004[0].details["attachment_count"] == 3

    @staticmethod
    def test_no_attachments_silent() -> None:
        """Regular Text / Link annotations don't trigger the attachment check."""
        doc = _doc_with_annotations("/Text", "/Link", "/Stamp")
        findings = StructureAnalyzer().analyze(doc, events=[])
        struct_004 = [f for f in findings if f.inspection_id == "LPDF_STRUCT_004"]
        assert struct_004 == []

    @staticmethod
    def test_empty_annotations_silent() -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        )
        findings = StructureAnalyzer().analyze(doc, events=[])
        struct_004 = [f for f in findings if f.inspection_id == "LPDF_STRUCT_004"]
        assert struct_004 == []

    @staticmethod
    def test_catalog_path_still_fires() -> None:
        """/Names /EmbeddedFiles path remains the primary detection —
        when both catalog tree + annotation exist, the catalog path wins
        (it's the canonical location) and we don't double-emit."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            catalog={"/Names": {"/EmbeddedFiles": {"/Names": []}}},
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    annotations=[
                        PdfAnnotation(
                            subtype="/FileAttachment",
                            rect=PdfBox(0, 0, 50, 50),
                            flags=4,
                            contents="",
                            page_num=1,
                        )
                    ],
                )
            ],
        )
        findings = StructureAnalyzer().analyze(doc, events=[])
        struct_004 = [f for f in findings if f.inspection_id == "LPDF_STRUCT_004"]
        assert len(struct_004) == 1
        assert struct_004[0].details["source"] == "catalog_names_tree"
