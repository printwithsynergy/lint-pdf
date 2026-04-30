"""Unit tests for ``AI_PHARMA_001`` after WS-2 swap.

Mirrors ``test_eu_fir_1169.py`` — same 7 disputed findings in the
Opus audit, same root cause, same structural fix (read composed
Tm x CTM scale). The category-gating that also belongs to this
rule lands in WS-3 and is tested separately.
"""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.pharma_font import (
    PharmaFontAnalyzer,
)
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


def _ctx(document, events=None, pdf_bytes=b"", ai_config=None):
    """Build an AnalyzerContext for analyze_v2 calls."""
    from lintpdf.plugin.protocol import AnalyzerContext

    return AnalyzerContext(
        document=document,
        events=events or [],
        pdf_bytes=pdf_bytes,
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


def _doc_eu(page_num: int = 1) -> SemanticDocument:
    """Build a doc whose content stream triggers the analyzer's EU
    auto-detection path so the pharma check actually runs."""
    page = SemanticPage(
        page_num=page_num,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=b"(Patient Information Leaflet) Tj",
    )
    page.fonts["F1"] = PdfFont(
        name="F1",
        base_font="Helvetica",
        font_type="Type1",
        embedded=False,
        subset=False,
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def _text_event(
    *,
    page_num: int = 1,
    font_size: float,
    tm_scale: float = 1.0,
    ctm_scale: float = 1.0,
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        text_matrix=TransformationMatrix(a=tm_scale, d=tm_scale),
        ctm=TransformationMatrix(a=ctm_scale, d=ctm_scale),
        bbox=(100.0, 100.0, 200.0, 140.0),
    )


def test_large_logo_does_not_flag_pharma_min() -> None:
    """Matches the 7 disputed PHARMA_001 findings on Nutrops:
    Tf=1.0, Tm.a=72, CTM.a=1.5 → 108 pt composed."""
    doc = _doc_eu()
    event = _text_event(font_size=1.0, tm_scale=72.0, ctm_scale=1.5)
    findings = PharmaFontAnalyzer().analyze_v2(_ctx(doc, events=[event], pdf_bytes=b""))
    pharma = [f for f in findings if f.inspection_id == "AI_PHARMA_001"]
    assert pharma == [], f"expected no pharma finding for 108pt logo; got {len(pharma)}"


def test_tiny_text_still_flags_pharma_min() -> None:
    """6 pt at identity matrices - x-height ≈ 1.1 mm, below the
    1.4 mm EU pharma minimum. Must still fire."""
    doc = _doc_eu()
    event = _text_event(font_size=6.0)
    findings = PharmaFontAnalyzer().analyze_v2(_ctx(doc, events=[event], pdf_bytes=b""))
    pharma = [f for f in findings if f.inspection_id == "AI_PHARMA_001"]
    assert len(pharma) == 1


class _Cfg:
    """Stand-in for TenantAIConfig — analyzer only reads the
    category / market attributes via ``getattr``."""

    def __init__(self, industry_type: str | None = None) -> None:
        self.industry_type = industry_type
        self.regulatory_market = None
        self.default_package_surface_area_cm2 = None


def test_dietary_supplement_industry_skips_analyzer() -> None:
    """WS-3 category gate: a dietary supplement product should
    produce zero pharma findings even when the same 6 pt text
    would otherwise flag as below the pharma minimum."""
    doc = _doc_eu()
    event = _text_event(font_size=6.0)
    cfg = {"industry_type": "dietary_supplement"}
    findings = PharmaFontAnalyzer().analyze_v2(
        _ctx(doc, events=[event], pdf_bytes=b"", ai_config=cfg)
    )
    pharma = [f for f in findings if f.inspection_id == "AI_PHARMA_001"]
    assert pharma == []


def test_unknown_industry_runs_analyzer() -> None:
    """Conservative default: unset industry_type still fires."""
    doc = _doc_eu()
    event = _text_event(font_size=6.0)
    cfg: dict = {"industry_type": None}
    findings = PharmaFontAnalyzer().analyze_v2(
        _ctx(doc, events=[event], pdf_bytes=b"", ai_config=cfg)
    )
    pharma = [f for f in findings if f.inspection_id == "AI_PHARMA_001"]
    assert len(pharma) == 1
