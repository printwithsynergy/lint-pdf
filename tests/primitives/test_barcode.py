"""Tests for barcode primitives (Tier-0 Batch 11)."""

from __future__ import annotations

from siftpdf.primitives import REGISTRY
from siftpdf.primitives import barcode as barcode_p


def test_registry_contains_nine_barcode_primitives():
    expected = {
        "is_barcode",
        "symbology",
        "is_1d",
        "is_2d",
        "narrow_bar_width",
        "quiet_zone",
        "is_decodable",
        "decoded_value",
        "gs1_compliant",
    }
    assert REGISTRY.get("barcode", {}).keys() == expected


# ---- is_barcode + symbology -----------------------------------------


def test_is_barcode_explicit_flag():
    assert barcode_p.is_barcode({"is_barcode": True}) is True


def test_is_barcode_via_classification():
    assert barcode_p.is_barcode({"object_class": "barcode"}) is True
    assert barcode_p.is_barcode({"kind": "QR"}) is True


def test_is_barcode_via_symbology():
    assert barcode_p.is_barcode({"symbology": "EAN-13"}) is True


def test_is_barcode_false_when_no_signals():
    assert barcode_p.is_barcode({"object_class": "image"}) is False
    assert barcode_p.is_barcode({}) is False


def test_symbology_canonicalization():
    assert barcode_p.symbology({"symbology": "qr-code"}) == "QR"
    assert barcode_p.symbology({"format": "code 128"}) == "CODE128"
    assert barcode_p.symbology({"barcode_type": "DataMatrix"}) == "DATAMATRIX"
    assert barcode_p.symbology({"symbology": "ean13"}) == "EAN-13"
    assert barcode_p.symbology({"symbology": "PDF-417"}) == "PDF417"
    assert barcode_p.symbology({}) is None


# ---- is_1d / is_2d --------------------------------------------------


def test_is_1d_true_for_linear():
    assert barcode_p.is_1d({"symbology": "EAN-13"}) is True
    assert barcode_p.is_1d({"symbology": "Code 128"}) is True
    assert barcode_p.is_1d({"symbology": "ITF-14"}) is True


def test_is_1d_false_for_matrix():
    assert barcode_p.is_1d({"symbology": "QR"}) is False


def test_is_2d_true_for_matrix():
    assert barcode_p.is_2d({"symbology": "QR"}) is True
    assert barcode_p.is_2d({"symbology": "DataMatrix"}) is True
    assert barcode_p.is_2d({"symbology": "PDF417"}) is True
    assert barcode_p.is_2d({"symbology": "AZTEC"}) is True


def test_is_2d_false_for_linear():
    assert barcode_p.is_2d({"symbology": "EAN-13"}) is False


def test_is_1d_and_2d_false_for_unknown_symbology():
    assert barcode_p.is_1d({}) is False
    assert barcode_p.is_2d({}) is False
    assert barcode_p.is_1d({"symbology": "MADEUP"}) is False
    assert barcode_p.is_2d({"symbology": "MADEUP"}) is False


# ---- bar width + quiet zone -----------------------------------------


def test_narrow_bar_width_explicit():
    assert barcode_p.narrow_bar_width({"narrow_bar_width": 1.4}) == 1.4
    assert barcode_p.narrow_bar_width({"x_dimension": 0.66}) == 0.66


def test_narrow_bar_width_none_when_missing():
    assert barcode_p.narrow_bar_width({}) is None


def test_narrow_bar_width_none_for_invalid():
    assert barcode_p.narrow_bar_width({"narrow_bar_width": "wide"}) is None


def test_quiet_zone_tuple():
    qz = barcode_p.quiet_zone({"quiet_zone": [10, 20, 30, 40]})
    assert qz == (10.0, 20.0, 30.0, 40.0)


def test_quiet_zone_none_when_wrong_shape():
    assert barcode_p.quiet_zone({"quiet_zone": [10, 20]}) is None
    assert barcode_p.quiet_zone({"quiet_zone": "10,20,30,40"}) is None
    assert barcode_p.quiet_zone({}) is None


# ---- is_decodable + decoded_value -----------------------------------


def test_decoded_value_text():
    assert barcode_p.decoded_value({"decoded_value": "0123456789012"}) == "0123456789012"
    assert barcode_p.decoded_value({"value": "Hello"}) == "Hello"


def test_decoded_value_bytes_decoded():
    assert barcode_p.decoded_value({"payload": b"abc"}) == "abc"


def test_decoded_value_none_when_absent():
    assert barcode_p.decoded_value({}) is None


def test_is_decodable_explicit_flag():
    assert barcode_p.is_decodable({"is_decodable": True}) is True


def test_is_decodable_via_decoded_value():
    assert barcode_p.is_decodable({"decoded_value": "x"}) is True


def test_is_decodable_false_when_no_value():
    assert barcode_p.is_decodable({}) is False


# ---- gs1_compliant --------------------------------------------------


def test_gs1_compliant_via_parenthesized_AI():  # noqa: N802
    assert barcode_p.gs1_compliant({"value": "(01)09501234543213(17)260101"}) is True


def test_gs1_compliant_via_fnc1_prefix():
    # ]C1 is the GS1 AIM symbology indicator
    assert barcode_p.gs1_compliant({"decoded_value": "]C10109501234543213"}) is True


def test_gs1_compliant_via_ascii_fnc1():
    assert barcode_p.gs1_compliant({"decoded_value": "\x1d0109501234543213"}) is True


def test_gs1_compliant_false_for_plain_payload():
    assert barcode_p.gs1_compliant({"decoded_value": "0123456789012"}) is False


def test_gs1_compliant_false_when_no_payload():
    assert barcode_p.gs1_compliant({}) is False


def test_gs1_compliant_explicit_override():
    assert barcode_p.gs1_compliant({"gs1_compliant": True, "decoded_value": "x"}) is True
    assert barcode_p.gs1_compliant({"gs1_compliant": False, "decoded_value": "(01)x"}) is False
