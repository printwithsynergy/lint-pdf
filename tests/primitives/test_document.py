"""Tests for document/metadata primitives (Tier-0 Batch 10)."""

from __future__ import annotations

from siftpdf.primitives import REGISTRY
from siftpdf.primitives import document as doc_p


def test_registry_includes_batch_10_primitives():
    expected_new = {
        "pdf_version",
        "is_pdf_x",
        "pdf_x_part",
        "is_pdf_a",
        "pdf_a_part",
        "is_pdf_va",
        "has_xmp",
        "acroform_present",
        "has_javascript",
        "has_embedded_files",
        "has_output_intent",
        "output_intent_subtype",
        "is_linearized",
        "signature_count",
    }
    actual = REGISTRY.get("doc", {}).keys()
    assert expected_new.issubset(actual)


# ---- pdf version ------------------------------------------------------


def test_pdf_version_from_doc():
    assert doc_p.pdf_version({"pdf_version": "1.7"}) == "1.7"


def test_pdf_version_from_catalog():
    assert doc_p.pdf_version({"Catalog": {"Version": "/2.0"}}) == "2.0"


def test_pdf_version_none_when_absent():
    assert doc_p.pdf_version({}) is None


# ---- PDF/X ------------------------------------------------------------


def test_is_pdf_x_via_info_dict():
    doc = {"Info": {"GTS_PDFXVersion": "PDF/X-4"}}
    assert doc_p.is_pdf_x(doc) is True
    assert doc_p.pdf_x_part(doc) == "PDF/X-4"


def test_is_pdf_x_via_xmp():
    xmp = b"<rdf:Description xmlns:pdfx='...'>PDF/X-1a</rdf:Description>"
    doc = {"Catalog": {"Metadata": xmp}}
    assert doc_p.is_pdf_x(doc) is True
    assert doc_p.pdf_x_part(doc) == "PDF/X-1a"


def test_is_pdf_x_false_when_absent():
    assert doc_p.is_pdf_x({}) is False
    assert doc_p.pdf_x_part({}) is None


# ---- PDF/A ------------------------------------------------------------


def test_is_pdf_a_via_xmp():
    xmp = (
        "<rdf:Description xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>"
        "<pdfaid:part>2</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance>"
        "</rdf:Description>"
    )
    doc = {"Catalog": {"Metadata": xmp}}
    assert doc_p.is_pdf_a(doc) is True
    assert doc_p.pdf_a_part(doc) == "PDF/A-2b"


def test_pdf_a_part_without_conformance():
    xmp = "<pdfaid:part>3</pdfaid:part>"
    doc = {"Catalog": {"Metadata": xmp}}
    assert doc_p.pdf_a_part(doc) == "PDF/A-3"


def test_is_pdf_a_false_when_no_xmp():
    assert doc_p.is_pdf_a({}) is False


# ---- PDF/UA -----------------------------------------------------------


def test_is_pdf_va_via_xmp():
    xmp = "<pdfuaid:part>1</pdfuaid:part>"
    doc = {"Catalog": {"Metadata": xmp}}
    assert doc_p.is_pdf_va(doc) is True


def test_is_pdf_va_false_when_absent():
    assert doc_p.is_pdf_va({}) is False


# ---- has_xmp / acroform / javascript / embedded ---------------------


def test_has_xmp_when_metadata_stream_present():
    assert doc_p.has_xmp({"Catalog": {"Metadata": "<x>"}}) is True
    assert doc_p.has_xmp({}) is False


def test_acroform_present_with_fields():
    doc = {"Catalog": {"AcroForm": {"Fields": [{"FT": "Tx"}]}}}
    assert doc_p.acroform_present(doc) is True


def test_acroform_present_false_when_fields_empty():
    assert doc_p.acroform_present({"Catalog": {"AcroForm": {"Fields": []}}}) is False


def test_acroform_present_false_when_acroform_missing():
    assert doc_p.acroform_present({}) is False


def test_has_javascript_via_names_tree():
    doc = {"Catalog": {"Names": {"JavaScript": {"Names": []}}}}
    assert doc_p.has_javascript(doc) is True


def test_has_javascript_via_open_action():
    doc = {"Catalog": {"OpenAction": {"S": "/JavaScript", "JS": "app.alert(1)"}}}
    assert doc_p.has_javascript(doc) is True


def test_has_javascript_false_when_absent():
    assert doc_p.has_javascript({}) is False


def test_has_embedded_files_via_names_tree():
    doc = {"Catalog": {"Names": {"EmbeddedFiles": {"Names": []}}}}
    assert doc_p.has_embedded_files(doc) is True


def test_has_embedded_files_false_when_absent():
    assert doc_p.has_embedded_files({}) is False


# ---- output intent ----------------------------------------------------


def test_has_output_intent_when_array_non_empty():
    doc = {"Catalog": {"OutputIntents": [{"S": "/GTS_PDFX"}]}}
    assert doc_p.has_output_intent(doc) is True
    assert doc_p.output_intent_subtype(doc) == "GTS_PDFX"


def test_has_output_intent_false_when_empty():
    assert doc_p.has_output_intent({"Catalog": {"OutputIntents": []}}) is False
    assert doc_p.output_intent_subtype({"Catalog": {"OutputIntents": []}}) is None


def test_output_intent_subtype_none_when_missing():
    assert doc_p.output_intent_subtype({}) is None


# ---- linearization + signatures --------------------------------------


def test_is_linearized():
    assert doc_p.is_linearized({"is_linearized": True}) is True
    assert doc_p.is_linearized({"linearized": True}) is True
    assert doc_p.is_linearized({}) is False


def test_signature_count_explicit_int():
    assert doc_p.signature_count({"signature_count": 3}) == 3


def test_signature_count_from_acroform_fields():
    doc = {
        "Catalog": {
            "AcroForm": {
                "Fields": [
                    {"FT": "Tx"},
                    {"FT": "Sig"},
                    {"FT": "/Sig"},
                ]
            }
        }
    }
    assert doc_p.signature_count(doc) == 2


def test_signature_count_zero_when_no_acroform():
    assert doc_p.signature_count({}) == 0
