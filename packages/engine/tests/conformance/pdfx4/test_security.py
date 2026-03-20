"""Tests for PDF/X-4 security checks (PDFX4-063-065)."""

from __future__ import annotations

from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._security import validate_security
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(
    is_encrypted: bool = False,
    trailer: dict[str, Any] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=is_encrypted,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        trailer=trailer or {},
    )


class TestEncryption:
    @staticmethod
    def test_encrypted_aground() -> None:
        f = validate_security(_doc(is_encrypted=True))
        ids = [x for x in f if x.inspection_id == "PDFX4-063"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    @staticmethod
    def test_not_encrypted_ok() -> None:
        f = validate_security(_doc())
        assert not [x for x in f if x.inspection_id == "PDFX4-063"]


class TestSecurityHandler:
    @staticmethod
    def test_encrypt_in_trailer() -> None:
        f = validate_security(_doc(trailer={"/Encrypt": {"/Filter": "/Standard"}}))
        ids = [x for x in f if x.inspection_id == "PDFX4-064"]
        assert len(ids) == 1

    @staticmethod
    def test_permissions() -> None:
        f = validate_security(_doc(trailer={"/Encrypt": {"/Filter": "/Standard", "/P": -3904}}))
        ids = [x for x in f if x.inspection_id == "PDFX4-065"]
        assert len(ids) == 1
