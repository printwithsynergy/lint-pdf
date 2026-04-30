"""Tests for PDF/X-4 transparency checks (PDFX4-043-048)."""

from __future__ import annotations

from typing import Any

from siftpdf.analyzers.finding import Severity
from siftpdf.conformance.pdfx4._transparency import validate_transparency
from siftpdf.semantic.events import OpacityChangedEvent
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(
    pages: list[SemanticPage] | None = None,
    output_intents: list[dict[str, Any]] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        output_intents=output_intents or [],
    )


def _opacity_event(
    sa: float = 1.0,
    nsa: float = 1.0,
    blend_mode: str | None = None,
    page_num: int = 1,
) -> OpacityChangedEvent:
    return OpacityChangedEvent(
        operator="gs",
        page_num=page_num,
        operator_index=0,
        stroking_alpha=sa,
        non_stroking_alpha=nsa,
        blend_mode=blend_mode,
    )


class TestTransparencyPresence:
    @staticmethod
    def test_has_transparency_advisory() -> None:
        f = validate_transparency(_doc(), [_opacity_event(nsa=0.5)])
        ids = [x for x in f if x.inspection_id == "PDFX4-043"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_no_transparency_ok() -> None:
        f = validate_transparency(_doc(), [_opacity_event(sa=1.0, nsa=1.0)])
        assert not [x for x in f if x.inspection_id == "PDFX4-043"]


class TestGroupColorSpace:
    @staticmethod
    def test_group_cs_conflicts_with_intent() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/CS": "DeviceRGB"},
        )
        intent = {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/ColorSpace": "CMYK"}}
        f = validate_transparency(_doc(pages=[page], output_intents=[intent]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-044"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING

    @staticmethod
    def test_group_cs_matches_intent_ok() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/CS": "DeviceCMYK"},
        )
        intent = {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/ColorSpace": "CMYK"}}
        f = validate_transparency(_doc(pages=[page], output_intents=[intent]), [])
        assert not [x for x in f if x.inspection_id == "PDFX4-044"]


class TestBlendModes:
    @staticmethod
    def test_non_standard_blend_mode_aground() -> None:
        f = validate_transparency(_doc(), [_opacity_event(nsa=0.5, blend_mode="CustomBlend")])
        ids = [x for x in f if x.inspection_id == "PDFX4-046"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_standard_blend_mode_ok() -> None:
        f = validate_transparency(_doc(), [_opacity_event(nsa=0.5, blend_mode="Multiply")])
        assert not [x for x in f if x.inspection_id == "PDFX4-046"]


class TestSoftMask:
    @staticmethod
    def test_soft_mask_cs_advisory() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/SMaskCS": "DeviceGray"},
        )
        f = validate_transparency(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-047"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestIsolatedKnockout:
    @staticmethod
    def test_isolated_knockout_advisory() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/I": True, "/K": True},
        )
        f = validate_transparency(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-048"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_isolated_only_ok() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/I": True, "/K": False},
        )
        f = validate_transparency(_doc(pages=[page]), [])
        assert not [x for x in f if x.inspection_id == "PDFX4-048"]
