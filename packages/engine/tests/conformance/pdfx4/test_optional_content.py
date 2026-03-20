"""Tests for PDF/X-4 optional content checks (PDFX4-066-070)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._optional_content import validate_optional_content
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(catalog: dict[str, Any] | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        catalog=catalog or {},
    )


class TestNoOcProperties:
    def test_no_oc_properties_ok(self) -> None:
        f = validate_optional_content(_doc())
        assert len(f) == 0


class TestMissingDefaultConfig:
    def test_missing_d_delay(self) -> None:
        f = validate_optional_content(_doc(catalog={"/OCProperties": {}}))
        ids = [x for x in f if x.inspection_id == "PDFX4-066"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL


class TestBaseState:
    def test_base_state_off_delay(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {"/BaseState": "OFF"},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        ids = [x for x in f if x.inspection_id == "PDFX4-067"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_base_state_on_ok(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {"/BaseState": "ON"},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        assert not [x for x in f if x.inspection_id == "PDFX4-067"]

    def test_base_state_default_on(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        assert not [x for x in f if x.inspection_id == "PDFX4-067"]


class TestOffLayers:
    def test_layers_off_advisory(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {"/OFF": ["Layer1", "Layer2"]},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        ids = [x for x in f if x.inspection_id == "PDFX4-068"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestOcgsArray:
    def test_empty_ocgs_delay(self) -> None:
        f = validate_optional_content(_doc(catalog={"/OCProperties": {"/D": {}, "/OCGs": []}}))
        ids = [x for x in f if x.inspection_id == "PDFX4-069"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_ocgs_present_ok(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        assert not [x for x in f if x.inspection_id == "PDFX4-069"]


class TestAsTriggers:
    def test_as_triggers_delay(self) -> None:
        f = validate_optional_content(
            _doc(
                catalog={
                    "/OCProperties": {
                        "/D": {"/AS": [{"Event": "View"}]},
                        "/OCGs": [{"name": "Layer1"}],
                    }
                }
            )
        )
        ids = [x for x in f if x.inspection_id == "PDFX4-070"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL
