"""Tests for LPDF_IMG_018 — broken image XObject references.

The check scans each page's /Resources /XObject dictionary and flags
entries that don't resolve to a legitimate Image or Form XObject. Three
failure modes are reported: dangling_indirect_ref, missing_subtype,
wrong_subtype.
"""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.image import ImageAnalyzer
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document_with_xobjects(xobjects: dict) -> SemanticDocument:
    """Build a one-page SemanticDocument with the given XObject resource dict."""
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                resources={"/XObject": xobjects},
            )
        ],
    )


class TestBrokenImageRefs:
    """LPDF_IMG_018 — dangling / wrong-type XObject references."""

    @staticmethod
    def test_dangling_indirect_ref_fires() -> None:
        """An XObject entry resolved to None → dangling_indirect_ref finding."""
        doc = _make_document_with_xobjects({"/Im1": None})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_IMG_018"
        assert f.severity == Severity.ERROR
        assert f.details["resource_name"] == "/Im1"
        assert f.details["failure_mode"] == "dangling_indirect_ref"
        assert f.details["resolved_subtype"] is None

    @staticmethod
    def test_shared_ref_string_is_dangling() -> None:
        """pikepdf cycle-detection sentinel string → dangling_indirect_ref."""
        doc = _make_document_with_xobjects({"/ImCycle": "<shared ref: 5 0 R>"})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "dangling_indirect_ref"

    @staticmethod
    def test_missing_subtype_fires() -> None:
        """An XObject dict with no /Subtype key is unrenderable."""
        doc = _make_document_with_xobjects(
            {"/Im2": {"/Width": 100, "/Height": 100}}  # no /Subtype
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "missing_subtype"
        assert findings[0].details["resolved_subtype"] is None

    @staticmethod
    def test_wrong_subtype_fires() -> None:
        """A /Subtype other than /Image or /Form → wrong_subtype."""
        doc = _make_document_with_xobjects(
            {"/Im3": {"/Subtype": "/PS", "/Length": 10}}  # deprecated PostScript XObject
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "wrong_subtype"
        assert findings[0].details["resolved_subtype"] == "/PS"

    @staticmethod
    def test_valid_image_xobject_silent() -> None:
        """A legit /Subtype=/Image XObject → no finding."""
        doc = _make_document_with_xobjects(
            {"/Im4": {"/Subtype": "/Image", "/Width": 100, "/Height": 100}}
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert findings == []

    @staticmethod
    def test_form_xobject_silent() -> None:
        """A legit /Subtype=/Form XObject → no finding (reusable graphics)."""
        doc = _make_document_with_xobjects(
            {"/Fm1": {"/Subtype": "/Form", "/BBox": [0, 0, 100, 100]}}
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert findings == []

    @staticmethod
    def test_mixed_dict_reports_only_broken() -> None:
        """A resource dict with both valid and broken entries → only broken flagged."""
        doc = _make_document_with_xobjects(
            {
                "/ImGood": {"/Subtype": "/Image", "/Width": 100, "/Height": 100},
                "/ImBroken": None,
                "/FmGood": {"/Subtype": "/Form", "/BBox": [0, 0, 100, 100]},
            }
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].details["resource_name"] == "/ImBroken"
        assert findings[0].details["failure_mode"] == "dangling_indirect_ref"

    @staticmethod
    def test_non_dict_xobject_entry_is_wrong_type() -> None:
        """An XObject entry that's an integer / list → wrong_subtype."""
        doc = _make_document_with_xobjects({"/Im5": 42})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "wrong_subtype"
        assert findings[0].details["resolved_subtype"] == "int"

    @staticmethod
    def test_no_xobject_dict_silent() -> None:
        """A page with no /XObject in resources → no finding."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), resources={})],
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert findings == []

    @staticmethod
    def test_integration_via_analyze() -> None:
        """Full analyze() call routes through _check_broken_image_refs."""
        doc = _make_document_with_xobjects({"/Im1": None})
        findings = ImageAnalyzer().analyze(doc, events=[])
        broken = [f for f in findings if f.inspection_id == "LPDF_IMG_018"]
        assert len(broken) == 1
