"""Tests for PDF/X-4 file structure checks (PDFX4-001-004, 080-084)."""

from __future__ import annotations

from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._file_structure import validate_file_structure
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(
    version: str = "1.7",
    catalog: dict[str, Any] | None = None,
    trailer: dict[str, Any] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version=version,
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        catalog=catalog or {},
        trailer=trailer or {},
    )


class TestPdfVersion:
    @staticmethod
    def test_version_below_16_aground() -> None:
        f = validate_file_structure(_doc(version="1.4"))
        ids = [x for x in f if x.inspection_id == "PDFX4-001"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    @staticmethod
    def test_version_16_ok() -> None:
        f = validate_file_structure(_doc(version="1.6"))
        assert not [x for x in f if x.inspection_id == "PDFX4-001"]

    @staticmethod
    def test_version_20_ok() -> None:
        f = validate_file_structure(_doc(version="2.0"))
        assert not [x for x in f if x.inspection_id == "PDFX4-001"]

    @staticmethod
    def test_empty_version() -> None:
        f = validate_file_structure(_doc(version=""))
        ids = {x.inspection_id for x in f}
        assert "PDFX4-001" in ids
        assert "PDFX4-002" in ids


class TestTrailerId:
    @staticmethod
    def test_missing_id_squall() -> None:
        f = validate_file_structure(_doc(trailer={}))
        ids = [x for x in f if x.inspection_id == "PDFX4-083"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    @staticmethod
    def test_id_present_ok() -> None:
        f = validate_file_structure(_doc(trailer={"/ID": ["abc", "def"]}))
        assert not [x for x in f if x.inspection_id == "PDFX4-083"]


class TestIncrementalUpdates:
    @staticmethod
    def test_prev_advisory() -> None:
        f = validate_file_structure(_doc(trailer={"/Prev": 1234, "/ID": ["a", "b"]}))
        ids = [x for x in f if x.inspection_id == "PDFX4-084"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestLinearized:
    @staticmethod
    def test_linearized_in_catalog() -> None:
        f = validate_file_structure(
            _doc(catalog={"/Linearized": "1.0"}, trailer={"/ID": ["a", "b"]})
        )
        ids = [x for x in f if x.inspection_id == "PDFX4-004"]
        assert len(ids) == 1
