"""Tests for Batch 10b — Tier-5 deferred (N01/N04/N06/N08/N09/N10).

Covers:
  - LPDF_PDFVT_STRUCTURE  (T5-N01)
  - LPDF_TOBACCO_WARNING_AREA  (T5-N04)
  - LPDF_BARCODE_GS1_AI  (T5-N08)
  - LPDF_BARCODE_UDI / LPDF_BARCODE_EU_DPP  (T5-N06)
  - LPDF_DIGIMARC_HINT  (T5-N09)
  - LPDF_GRAIN_MISSING  (T5-N10)
"""

from __future__ import annotations

from siftpdf.ai.analyzers.regulatory_compliance.tobacco import TobaccoWarningAnalyzer
from siftpdf.analyzers.barcode_validation import (
    validate_eu_dpp_payload,
    validate_gs1_ai_payload,
    validate_udi_payload,
)
from siftpdf.analyzers.metadata import MetadataAnalyzer
from siftpdf.conformance.pdfvt import check_pdfvt_structure
from siftpdf.semantic.events import TextRenderedEvent
from siftpdf.semantic.graphics_state import TransformationMatrix
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _ctx(document, events=None, pdf_bytes=b"", ai_config=None):
    """Build an AnalyzerContext for analyze_v2 calls."""
    from siftpdf.plugin.protocol import AnalyzerContext

    return AnalyzerContext(
        document=document,
        events=events or [],
        pdf_bytes=pdf_bytes,
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


def _doc(**kwargs) -> SemanticDocument:
    return SemanticDocument(
        version=kwargs.get("version", "1.7"),
        page_count=1,
        is_encrypted=False,
        info_dict=kwargs.get("info_dict", {}),
        catalog=kwargs.get("catalog", {}),
        output_intents=kwargs.get("output_intents", []),
        metadata_stream=kwargs.get("metadata_stream"),
        trailer={},
        pages=kwargs.get(
            "pages",
            [
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    content_stream=kwargs.get("content_stream", b""),
                )
            ],
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# T5-N01 — PDF/VT structural check
# ─────────────────────────────────────────────────────────────────────


class TestPdfVtStructure:
    @staticmethod
    def test_silent_when_no_pdfvt_declaration() -> None:
        xmp = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'/>"
        doc = _doc(metadata_stream=xmp)
        assert check_pdfvt_structure(doc) == []

    @staticmethod
    def test_pdfvt_declared_without_dpart_root_fires() -> None:
        xmp = (
            b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b"PDF/VT-1"
            b'</x:xmpmeta><?xpacket end="r"?>'
        )
        doc = _doc(metadata_stream=xmp, catalog={})
        out = check_pdfvt_structure(doc)
        ids = [f.inspection_id for f in out]
        assert "LPDF_PDFVT_STRUCTURE" in ids
        f = next(f for f in out if f.inspection_id == "LPDF_PDFVT_STRUCTURE")
        assert "missing_dpart_root" in f.details["issues"]

    @staticmethod
    def test_pdfvt_with_dpart_root_silent() -> None:
        xmp = (
            b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b"PDF/VT-2"
            b'</x:xmpmeta><?xpacket end="r"?>'
        )
        doc = _doc(metadata_stream=xmp, catalog={"/DPartRoot": "<ref>"})
        assert check_pdfvt_structure(doc) == []


# ─────────────────────────────────────────────────────────────────────
# T5-N04 — Tobacco warning area
# ─────────────────────────────────────────────────────────────────────


class TestTobaccoWarningArea:
    @staticmethod
    def test_silent_on_non_tobacco() -> None:
        doc = _doc(content_stream=b"Premium chocolate bar")
        out = TobaccoWarningAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        assert out == []

    @staticmethod
    def test_small_warning_area_fires() -> None:
        text = b"Marlboro cigarettes. WARNING: SMOKING KILLS. Tobacco causes cancer."
        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=0,
                font_name="Helvetica",
                font_size=10.0,
                ctm=TransformationMatrix(1, 0, 0, 1, 0, 0),
                text_matrix=TransformationMatrix(1, 0, 0, 1, 0, 0),
                color_space="DeviceGray",
                color_values=(0.0,),
                rendering_mode=0,
                bbox=(50.0, 50.0, 100.0, 100.0),  # 50x50 = 2500pt2; page is 612*792
            )
        ]
        doc = _doc(content_stream=text)
        out = TobaccoWarningAnalyzer().analyze_v2(_ctx(doc, events=events, pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "LPDF_TOBACCO_WARNING_AREA" in ids


# ─────────────────────────────────────────────────────────────────────
# T5-N08 — GS1 AI syntax
# ─────────────────────────────────────────────────────────────────────


class TestGs1AiPayload:
    @staticmethod
    def test_valid_gtin_silent() -> None:
        # AI 01 (GTIN) + AI 17 (expiry).
        payload = "01" + "01234567890128" + "17" + "260101"
        out = validate_gs1_ai_payload(payload, page_num=1)
        assert out == []

    @staticmethod
    def test_short_gtin_fires() -> None:
        payload = "01" + "0123456789012"  # 13 digits; AI 01 wants exactly 14
        out = validate_gs1_ai_payload(payload, page_num=1)
        assert any(f.inspection_id == "LPDF_BARCODE_GS1_AI" for f in out)

    @staticmethod
    def test_unknown_ai_fires() -> None:
        payload = "01" + "01234567890128" + "99" + "AAAA"  # 99 not in our schema
        out = validate_gs1_ai_payload(payload, page_num=1)
        assert any(f.inspection_id == "LPDF_BARCODE_GS1_AI" for f in out)

    @staticmethod
    def test_non_gs1_payload_silent() -> None:
        payload = "https://example.com/product/12345"
        assert validate_gs1_ai_payload(payload, page_num=1) == []


# ─────────────────────────────────────────────────────────────────────
# T5-N06 — UDI / EU DPP
# ─────────────────────────────────────────────────────────────────────


class TestUdiAndEuDpp:
    @staticmethod
    def test_udi_with_required_ais_silent() -> None:
        # AI 01 (GTIN), AI 17 (expiry), AI 10 (lot), AI 21 (serial).
        payload = (
            "01"
            + "01234567890128"
            + "17"
            + "260101"
            + "10"
            + "LOT123"
            + "\x1d"
            + "21"
            + "SERIAL456"
        )
        assert validate_udi_payload(payload, page_num=1) == []

    @staticmethod
    def test_udi_missing_recommended_fires() -> None:
        payload = "01" + "01234567890128"  # GTIN only — no production AIs
        out = validate_udi_payload(payload, page_num=1)
        assert any(f.inspection_id == "LPDF_BARCODE_UDI" for f in out)

    @staticmethod
    def test_eu_dpp_https_silent() -> None:
        url = "https://dpp.europa.eu/products/abc-123"
        assert validate_eu_dpp_payload(url, page_num=1) == []

    @staticmethod
    def test_eu_dpp_http_fires() -> None:
        url = "http://dpp.europa.eu/products/abc-123"
        out = validate_eu_dpp_payload(url, page_num=1)
        assert any(f.inspection_id == "LPDF_BARCODE_EU_DPP" for f in out)

    @staticmethod
    def test_non_dpp_url_silent() -> None:
        assert validate_eu_dpp_payload("https://example.com/product/123", page_num=1) == []


# ─────────────────────────────────────────────────────────────────────
# T5-N09 — Digimarc hint
# ─────────────────────────────────────────────────────────────────────


class TestDigimarcHint:
    @staticmethod
    def test_no_digimarc_silent() -> None:
        xmp = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'><meta>nothing</meta></x:xmpmeta>"
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_DIGIMARC_HINT" for f in out)

    @staticmethod
    def test_digimarc_url_in_xmp_fires() -> None:
        xmp = (
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b"<extra>https://digimarc.com/asset/12345</extra>"
            b"</x:xmpmeta>"
        )
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert any(f.inspection_id == "LPDF_DIGIMARC_HINT" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T5-N10 — Grain direction
# ─────────────────────────────────────────────────────────────────────


class TestGrainMissing:
    @staticmethod
    def test_no_grain_metadata_fires() -> None:
        xmp = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'><meta>nothing</meta></x:xmpmeta>"
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert any(f.inspection_id == "LPDF_GRAIN_MISSING" for f in out)

    @staticmethod
    def test_grain_metadata_present_silent() -> None:
        xmp = (
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b"<gwg:grain>machine-direction</gwg:grain>"
            b"</x:xmpmeta>"
        )
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_GRAIN_MISSING" for f in out)
