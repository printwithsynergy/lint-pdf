"""Tests for LPDF_IMG_018 / 019 / 020 — broken image XObject references.

Three distinct inspection_ids, split by failure class so tenants can tune
severity per class in the rules editor:

  - LPDF_IMG_018: dangling indirect ref (xref slot absent, null object,
    or pikepdf cycle sentinel)
  - LPDF_IMG_019: entry is a dict with no /Subtype key
  - LPDF_IMG_020: entry is a dict with /Subtype that's neither /Image
    nor /Form (e.g., deprecated /PS), or a non-dict entry
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


class TestDanglingRef018:
    """LPDF_IMG_018 — dangling indirect reference."""

    @staticmethod
    def test_none_entry_fires() -> None:
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
    def test_shared_ref_sentinel_fires() -> None:
        """pikepdf cycle-detection sentinel string → dangling."""
        doc = _make_document_with_xobjects({"/ImCycle": "<shared ref: 5 0 R>"})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].inspection_id == "LPDF_IMG_018"
        assert findings[0].details["failure_mode"] == "dangling_indirect_ref"


class TestMissingSubtype019:
    """LPDF_IMG_019 — /Subtype key missing."""

    @staticmethod
    def test_missing_subtype_fires() -> None:
        doc = _make_document_with_xobjects(
            {"/Im2": {"/Width": 100, "/Height": 100}}  # no /Subtype
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_IMG_019"
        assert f.severity == Severity.ERROR
        assert f.details["failure_mode"] == "missing_subtype"
        assert f.details["resolved_subtype"] is None


class TestWrongSubtype020:
    """LPDF_IMG_020 — /Subtype present but unrecognised."""

    @staticmethod
    def test_ps_subtype_fires() -> None:
        """Deprecated PostScript XObject → wrong_subtype."""
        doc = _make_document_with_xobjects({"/Im3": {"/Subtype": "/PS", "/Length": 10}})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_IMG_020"
        assert f.severity == Severity.ERROR
        assert f.details["failure_mode"] == "wrong_subtype"
        assert f.details["resolved_subtype"] == "/PS"

    @staticmethod
    def test_non_dict_entry_fires() -> None:
        """An XObject entry that's an int / list → wrong_subtype."""
        doc = _make_document_with_xobjects({"/Im5": 42})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].inspection_id == "LPDF_IMG_020"
        assert findings[0].details["resolved_subtype"] == "int"

    @staticmethod
    def test_vendor_subtype_fires() -> None:
        """Any /Subtype that isn't /Image or /Form is flagged."""
        doc = _make_document_with_xobjects({"/Im6": {"/Subtype": "/SomeVendorThing"}})
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 1
        assert findings[0].inspection_id == "LPDF_IMG_020"


class TestValidRefsSilent:
    """Legitimate XObjects emit no finding regardless of inspection_id."""

    @staticmethod
    def test_image_xobject_silent() -> None:
        doc = _make_document_with_xobjects(
            {"/Im4": {"/Subtype": "/Image", "/Width": 100, "/Height": 100}}
        )
        assert ImageAnalyzer()._check_broken_image_refs(doc) == []

    @staticmethod
    def test_form_xobject_silent() -> None:
        doc = _make_document_with_xobjects(
            {"/Fm1": {"/Subtype": "/Form", "/BBox": [0, 0, 100, 100]}}
        )
        assert ImageAnalyzer()._check_broken_image_refs(doc) == []

    @staticmethod
    def test_no_xobject_dict_silent() -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), resources={})],
        )
        assert ImageAnalyzer()._check_broken_image_refs(doc) == []


class TestMixedDict:
    """A dict with mixed entries routes each to the correct ID."""

    @staticmethod
    def test_all_three_failure_modes_at_once() -> None:
        doc = _make_document_with_xobjects(
            {
                "/ImGood": {"/Subtype": "/Image", "/Width": 100, "/Height": 100},
                "/ImDangling": None,
                "/ImMissingSubtype": {"/Width": 50},
                "/ImWrongSubtype": {"/Subtype": "/PS"},
                "/FmGood": {"/Subtype": "/Form", "/BBox": [0, 0, 100, 100]},
            }
        )
        findings = ImageAnalyzer()._check_broken_image_refs(doc)
        assert len(findings) == 3
        by_name = {f.details["resource_name"]: f for f in findings}
        assert by_name["/ImDangling"].inspection_id == "LPDF_IMG_018"
        assert by_name["/ImMissingSubtype"].inspection_id == "LPDF_IMG_019"
        assert by_name["/ImWrongSubtype"].inspection_id == "LPDF_IMG_020"


class TestAnalyzeIntegration:
    @staticmethod
    def test_analyze_emits_dangling() -> None:
        doc = _make_document_with_xobjects({"/Im1": None})
        findings = ImageAnalyzer().analyze(doc, events=[])
        ids = {f.inspection_id for f in findings}
        assert "LPDF_IMG_018" in ids

    @staticmethod
    def test_analyze_emits_missing_subtype() -> None:
        doc = _make_document_with_xobjects({"/Im2": {"/Width": 100}})
        findings = ImageAnalyzer().analyze(doc, events=[])
        ids = {f.inspection_id for f in findings}
        assert "LPDF_IMG_019" in ids

    @staticmethod
    def test_analyze_emits_wrong_subtype() -> None:
        doc = _make_document_with_xobjects({"/Im3": {"/Subtype": "/PS"}})
        findings = ImageAnalyzer().analyze(doc, events=[])
        ids = {f.inspection_id for f in findings}
        assert "LPDF_IMG_020" in ids
