"""Tests for PDF/X-4 output intent checks (PDFX4-016-025)."""

from __future__ import annotations

from typing import Any

from lintpdf.analyzers.finding import Severity
from lintpdf.conformance.pdfx4._output_intent import validate_output_intent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(output_intents: list[dict[str, Any]] | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        output_intents=output_intents or [],
    )


_VALID_INTENT = {
    "/S": "/GTS_PDFX",
    "/OutputConditionIdentifier": "FOGRA39",
    "/RegistryName": "http://www.color.org",
    "/Info": "FOGRA39 coated",
}


class TestNoOutputIntent:
    @staticmethod
    def test_missing_output_intent_aground() -> None:
        f = validate_output_intent(_doc())
        ids = [x for x in f if x.inspection_id == "PDFX4-016"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_valid_intent_no_016() -> None:
        f = validate_output_intent(_doc(output_intents=[_VALID_INTENT]))
        assert not [x for x in f if x.inspection_id == "PDFX4-016"]


class TestGtsPdfxSubtype:
    @staticmethod
    def test_no_gts_pdfx_intent() -> None:
        intent = {"/S": "/GTS_PDFA1", "/OutputConditionIdentifier": "sRGB"}
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-017"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_valid_gts_pdfx() -> None:
        f = validate_output_intent(_doc(output_intents=[_VALID_INTENT]))
        assert not [x for x in f if x.inspection_id == "PDFX4-017"]


class TestOutputConditionIdentifier:
    @staticmethod
    def test_missing_oci() -> None:
        intent = {"/S": "/GTS_PDFX", "/Info": "test"}
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-018"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestIccProfile:
    @staticmethod
    def test_unregistered_no_profile_aground() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "CustomProfile",
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-019"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_registered_condition_ok() -> None:
        f = validate_output_intent(_doc(output_intents=[_VALID_INTENT]))
        assert not [x for x in f if x.inspection_id == "PDFX4-019"]

    @staticmethod
    def test_embedded_profile_ok() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "CustomProfile",
            "/DestOutputProfile": {"/N": 4, "/ColorSpace": "CMYK"},
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        assert not [x for x in f if x.inspection_id == "PDFX4-019"]

    @staticmethod
    def test_icc_version_low() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "Custom",
            "/DestOutputProfile": {"/ICCVersion": "1.5", "/ColorSpace": "CMYK"},
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-020"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING

    @staticmethod
    def test_icc_bad_profile_class() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "Custom",
            "/DestOutputProfile": {
                "/ColorSpace": "CMYK",
                "/ProfileClass": "scnr",
            },
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-021"]
        assert len(ids) == 1

    @staticmethod
    def test_icc_bad_color_space() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "Custom",
            "/DestOutputProfile": {"/ColorSpace": "XYZ"},
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-022"]
        assert len(ids) == 1


class TestMultipleIntents:
    @staticmethod
    def test_multiple_gts_pdfx_squall() -> None:
        f = validate_output_intent(_doc(output_intents=[_VALID_INTENT, _VALID_INTENT]))
        ids = [x for x in f if x.inspection_id == "PDFX4-023"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING


class TestRegistryAndInfo:
    @staticmethod
    def test_registered_missing_registry_name() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "FOGRA39",
            "/Info": "test",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-024"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_missing_info_string() -> None:
        intent = {
            "/S": "/GTS_PDFX",
            "/OutputConditionIdentifier": "FOGRA39",
            "/RegistryName": "http://www.color.org",
        }
        f = validate_output_intent(_doc(output_intents=[intent]))
        ids = [x for x in f if x.inspection_id == "PDFX4-025"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY
