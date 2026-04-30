"""Tests for Batch 9b regulatory analyzers (AI_ALC, AI_CANN, AI_COSM)."""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.alcohol import AlcoholLabelingAnalyzer
from lintpdf.ai.analyzers.regulatory_compliance.cannabis import CannabisLabelingAnalyzer
from lintpdf.ai.analyzers.regulatory_compliance.cosmetics import CosmeticsLabelingAnalyzer
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


def _doc(text: str) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        catalog={},
        trailer={},
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                content_stream=text.encode("latin-1", errors="replace"),
            )
        ],
    )


# ─────────────────────────────────────────────────────────────────────
# AI_ALC — Alcohol labeling
# ─────────────────────────────────────────────────────────────────────


class TestAlcohol:
    @staticmethod
    def test_silent_on_non_alcohol() -> None:
        doc = _doc("This is a chocolate bar with cocoa, sugar, milk.")
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        assert out == []

    @staticmethod
    def test_missing_all_required_elements() -> None:
        doc = _doc("Premium California Chardonnay wine — bottled at our estate.")
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_ALC_001" in ids
        f = next(f for f in out if f.inspection_id == "AI_ALC_001")
        missing = f.details["missing_elements"]
        assert "abv_declaration" in missing
        assert "ttb_government_warning" in missing

    @staticmethod
    def test_complete_label_silent() -> None:
        text = (
            "Cabernet Sauvignon 13.5% ALC/VOL. "
            "GOVERNMENT WARNING: According to the Surgeon General... "
            "Product of California, USA."
        )
        doc = _doc(text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        assert [f.inspection_id for f in out if f.inspection_id == "AI_ALC_001"] == []

    @staticmethod
    def test_format_violation_excess_precision() -> None:
        text = "Whisky 12.555% ALC/VOL. GOVERNMENT WARNING. Made in Scotland."
        doc = _doc(text)
        out = AlcoholLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_ALC_002" in ids


# ─────────────────────────────────────────────────────────────────────
# AI_CANN — Cannabis labeling
# ─────────────────────────────────────────────────────────────────────


class TestCannabis:
    @staticmethod
    def test_silent_on_non_cannabis() -> None:
        doc = _doc("Vitamin D supplement 1000 IU per gummy.")
        out = CannabisLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        assert out == []

    @staticmethod
    def test_missing_required_warnings() -> None:
        doc = _doc("Premium edibles with 10mg THC per piece. Made by licensed producer.")
        out = CannabisLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_CANN_001" in ids
        f = next(f for f in out if f.inspection_id == "AI_CANN_001")
        assert "keep_out_of_reach_of_children" in f.details["missing_elements"]
        assert "cannabis_warning_symbol" in f.details["missing_elements"]

    @staticmethod
    def test_complete_cannabis_label_silent() -> None:
        text = (
            "Cannabis Gummies — 5mg THC per serving. 10 servings. Total THC: 50mg. "
            "Keep out of reach of children. California Universal Symbol shown. "
            "Licensed producer."
        )
        doc = _doc(text)
        out = CannabisLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        cann001 = [f for f in out if f.inspection_id == "AI_CANN_001"]
        assert cann001 == []

    @staticmethod
    def test_potency_arithmetic_mismatch() -> None:
        text = (
            "Cannabis chocolate bar — 5mg THC per serving, 10 servings. "
            "Total THC: 100mg. "
            "Keep out of reach of children. Universal Symbol. Licensed producer."
        )
        doc = _doc(text)
        out = CannabisLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_CANN_002" in ids


# ─────────────────────────────────────────────────────────────────────
# AI_COSM — Cosmetics labeling
# ─────────────────────────────────────────────────────────────────────


class TestCosmetics:
    @staticmethod
    def test_silent_on_non_cosmetic() -> None:
        doc = _doc("Organic almonds — 200g pack. Contains: almonds.")
        out = CosmeticsLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        assert out == []

    @staticmethod
    def test_missing_required_elements() -> None:
        doc = _doc("Luxury face cream — apply twice daily.")
        out = CosmeticsLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_COSM_001" in ids
        f = next(f for f in out if f.inspection_id == "AI_COSM_001")
        missing = f.details["missing_elements"]
        assert "ingredient_list" in missing
        assert "pao_symbol" in missing
        assert "batch_code" in missing

    @staticmethod
    def test_complete_cosmetic_label_silent() -> None:
        text = (
            "Luxury Face Cream 50ml. "
            "INGREDIENTS: AQUA, GLYCERIN, BUTYROSPERMUM PARKII, TOCOPHEROL. "
            "12M after opening. "
            "BATCH: A2024-039. "
            "Period after opening 12M."
        )
        doc = _doc(text)
        out = CosmeticsLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        cosm001 = [f for f in out if f.inspection_id == "AI_COSM_001"]
        assert cosm001 == []

    @staticmethod
    def test_inci_first_token_not_water() -> None:
        text = (
            "Body lotion 200ml. "
            "INGREDIENTS: PARABEN, AQUA, GLYCERIN, FRAGRANCE. "
            "12M after opening. BATCH: B2024-001."
        )
        doc = _doc(text)
        out = CosmeticsLabelingAnalyzer().analyze_v2(_ctx(doc, events=[], pdf_bytes=b""))
        ids = [f.inspection_id for f in out]
        assert "AI_COSM_002" in ids
