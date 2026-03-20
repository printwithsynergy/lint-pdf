"""Tests for PDF/X-4 restricted features checks (PDFX4-071-078)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._restricted_features import validate_restricted_features
from grounded.semantic.events import PrepressStateChangedEvent
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(
    catalog: dict[str, Any] | None = None,
    pages: list[SemanticPage] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        catalog=catalog or {},
    )


def _prepress_event(
    has_halftone: bool = False,
    has_transfer_function: bool = False,
) -> PrepressStateChangedEvent:
    return PrepressStateChangedEvent(
        operator="gs",
        page_num=1,
        operator_index=0,
        has_halftone=has_halftone,
        has_transfer_function=has_transfer_function,
    )


class TestJavaScript:
    def test_js_in_names_aground(self) -> None:
        catalog: dict[str, Any] = {"/Names": {"/JavaScript": {"Names": []}}}
        f = validate_restricted_features(_doc(catalog=catalog), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-071"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_js_in_open_action(self) -> None:
        catalog = {"/OpenAction": {"/S": "/JavaScript"}}
        f = validate_restricted_features(_doc(catalog=catalog), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-071"]
        assert len(ids) == 1

    def test_no_js_ok(self) -> None:
        f = validate_restricted_features(_doc(), [])
        assert not [x for x in f if x.inspection_id == "PDFX4-071"]


class TestLaunchActions:
    def test_launch_in_aa_aground(self) -> None:
        catalog = {"/AA": {"/O": {"/S": "/Launch"}}}
        f = validate_restricted_features(_doc(catalog=catalog), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-072"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND


class TestEmbeddedFiles:
    def test_embedded_files_aground(self) -> None:
        catalog: dict[str, Any] = {"/Names": {"/EmbeddedFiles": {"Names": []}}}
        f = validate_restricted_features(_doc(catalog=catalog), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-073"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND


class TestXfaForms:
    def test_xfa_aground(self) -> None:
        catalog = {"/AcroForm": {"/XFA": b"xfa_data"}}
        f = validate_restricted_features(_doc(catalog=catalog), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-074"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND


class TestTransferFunctions:
    def test_transfer_function_aground(self) -> None:
        f = validate_restricted_features(_doc(), [_prepress_event(has_transfer_function=True)])
        ids = [x for x in f if x.inspection_id == "PDFX4-075"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_no_transfer_ok(self) -> None:
        f = validate_restricted_features(_doc(), [_prepress_event()])
        assert not [x for x in f if x.inspection_id == "PDFX4-075"]


class TestHalftones:
    def test_halftone_advisory(self) -> None:
        f = validate_restricted_features(_doc(), [_prepress_event(has_halftone=True)])
        ids = [x for x in f if x.inspection_id == "PDFX4-076"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestPostScriptXObjects:
    def test_ps_xobject_aground(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/XObject": {"/PS1": {"/Subtype": "/PS"}}},
        )
        f = validate_restricted_features(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-077"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND


class TestExternalStreams:
    def test_external_stream_aground(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/XObject": {"/Im1": {"/Subtype": "/Image", "/F": "/path/to/file"}}},
        )
        f = validate_restricted_features(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-078"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND
