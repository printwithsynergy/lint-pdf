"""Tests for Batch 11 — promote partial gaps to present.

Covers:
  - LPDF_TEXT_SOFT_MASK (T2-TRN06)
  - AI_ALC_003 (T5-N05) — wine / spirits-specific TTB 27 CFR 4 / 5
"""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.alcohol import AlcoholLabelingAnalyzer
from lintpdf.analyzers.transparency import TransparencyAnalyzer
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _ctx(document, events=None, pdf_bytes=b"", ai_config=None):
    """Build an AnalyzerContext for analyze_v2 calls."""
    from lintpdf.plugin.protocol import AnalyzerContext

    return AnalyzerContext(
        document=document,
        events=events or [],
        pdf_bytes=pdf_bytes,
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


def _doc(**kwargs) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        info_dict={},
        catalog={},
        output_intents=[],
        metadata_stream=None,
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
# T2-TRN06 — text under soft mask
# ─────────────────────────────────────────────────────────────────────


class TestTextSoftMask:
    @staticmethod
    def test_soft_mask_with_text_fires() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ExtGState": {"/GS1": {"/SMask": "<ref>"}}},
        )
        doc = _doc(pages=[page])
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
            )
        ]
        out = TransparencyAnalyzer().analyze(doc, events)
        ids = [f.inspection_id for f in out]
        assert "LPDF_TEXT_SOFT_MASK" in ids

    @staticmethod
    def test_soft_mask_no_text_silent() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ExtGState": {"/GS1": {"/SMask": "<ref>"}}},
        )
        doc = _doc(pages=[page])
        out = TransparencyAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_TEXT_SOFT_MASK" for f in out)

    @staticmethod
    def test_no_soft_mask_silent() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ExtGState": {"/GS1": {"/SMask": "/None"}}},
        )
        doc = _doc(pages=[page])
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
            )
        ]
        out = TransparencyAnalyzer().analyze(doc, events)
        assert all(f.inspection_id != "LPDF_TEXT_SOFT_MASK" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T5-N05 — wine / spirits specific compliance
# ─────────────────────────────────────────────────────────────────────


class TestWineSpiritsCompliance:
    @staticmethod
    def test_wine_without_sulfites_fires() -> None:
        text = b"Cabernet Sauvignon 13.5% ALC/VOL. GOVERNMENT WARNING. Product of California, USA."
        doc = _doc(content_stream=text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        alc003 = [f for f in out if f.inspection_id == "AI_ALC_003"]
        assert len(alc003) >= 1
        assert any("missing_contains_sulfites" in f.details["issues"] for f in alc003)

    @staticmethod
    def test_wine_with_sulfites_silent_for_alc003() -> None:
        text = (
            b"Cabernet Sauvignon 13.5% ALC/VOL. GOVERNMENT WARNING. "
            b"Product of Napa Valley, California. Contains sulfites."
        )
        doc = _doc(content_stream=text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        alc003 = [f for f in out if f.inspection_id == "AI_ALC_003"]
        assert alc003 == []

    @staticmethod
    def test_estate_bottled_without_appellation_fires() -> None:
        text = (
            b"Pinot Noir Estate Bottled 13.0% ALC/VOL. GOVERNMENT WARNING. "
            b"Product of USA. Contains sulfites."
        )
        doc = _doc(content_stream=text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        alc003 = [f for f in out if f.inspection_id == "AI_ALC_003"]
        assert any("estate_bottled_without_appellation" in f.details["issues"] for f in alc003)

    @staticmethod
    def test_spirits_without_proof_fires() -> None:
        text = b"Premium Whisky 40% ALC/VOL. GOVERNMENT WARNING. Distilled in Scotland."
        doc = _doc(content_stream=text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        alc003 = [f for f in out if f.inspection_id == "AI_ALC_003"]
        assert any("missing_proof_statement" in f.details["issues"] for f in alc003)

    @staticmethod
    def test_spirits_with_proof_silent() -> None:
        text = b"Premium Whisky 40% ALC/VOL (80 proof). GOVERNMENT WARNING. Distilled in Scotland."
        doc = _doc(content_stream=text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        alc003 = [f for f in out if f.inspection_id == "AI_ALC_003"]
        assert alc003 == []
