"""Tests for the EPM v2 Tier-B analyzer (5 soft-rejection codes)."""

from __future__ import annotations

from siftpdf.analyzers import epm_v2_b
from siftpdf.epm import codes
from siftpdf.semantic.events import ImagePlacedEvent
from siftpdf.semantic.graphics_state import TransformationMatrix
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _document(
    *,
    page_count: int = 1,
    pages: list[SemanticPage] | None = None,
) -> SemanticDocument:
    if pages is None:
        pages = [
            SemanticPage(page_num=i + 1, media_box=PdfBox(0, 0, 612, 792))
            for i in range(page_count)
        ]
    return SemanticDocument(
        version="1.7",
        page_count=len(pages),
        is_encrypted=False,
        pages=pages,
    )


# ---- B1: process color count -------------------------------------------


def test_b1_quiet_for_pure_cmyk_doc():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={
            "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
        },
    )
    findings = epm_v2_b.detect_b1_process_color_count(
        _document(pages=[page]), limit=4
    )
    assert findings == []


def test_b1_fires_on_too_many_spots():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={
            "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
            "Spot1": PdfColorSpace(
                name="PANTONE 185 C", cs_type="Separation", components=1,
                colorant_names=("PANTONE 185 C",),
            ),
            "Spot2": PdfColorSpace(
                name="PANTONE 286 C", cs_type="Separation", components=1,
                colorant_names=("PANTONE 286 C",),
            ),
            "Spot3": PdfColorSpace(
                name="PANTONE 805 C", cs_type="Separation", components=1,
                colorant_names=("PANTONE 805 C",),
            ),
            "Spot4": PdfColorSpace(
                name="PANTONE Reflex Blue C", cs_type="Separation", components=1,
                colorant_names=("PANTONE Reflex Blue C",),
            ),
        },
    )
    findings = epm_v2_b.detect_b1_process_color_count(
        _document(pages=[page]), limit=4
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_PROCESS_COLOR_COUNT


def test_b1_ignores_cmyk_inside_separation_colorants():
    """Cyan / Magenta / Yellow / Black names don't count as spot plates."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={
            "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
            "SepCyan": PdfColorSpace(
                name="Cyan", cs_type="Separation", components=1,
                colorant_names=("Cyan",),
            ),
        },
    )
    findings = epm_v2_b.detect_b1_process_color_count(
        _document(pages=[page]), limit=4
    )
    assert findings == []


# ---- B3: bleed below min -----------------------------------------------


def test_b3_fires_when_bleed_zero():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(0, 0, 612, 792),
    )
    findings = epm_v2_b.detect_b3_bleed_below_min(
        _document(pages=[page]), min_bleed_pt=8.5
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_BLEED_BELOW_MIN


def test_b3_quiet_when_bleed_meets_min():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(9, 9, 603, 783),  # 9pt all sides
    )
    findings = epm_v2_b.detect_b3_bleed_below_min(
        _document(pages=[page]), min_bleed_pt=8.5
    )
    assert findings == []


def test_b3_one_finding_per_offending_page():
    page1 = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(9, 9, 603, 783),
    )
    page2 = SemanticPage(
        page_num=2,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(0, 0, 612, 792),
    )
    findings = epm_v2_b.detect_b3_bleed_below_min(
        _document(pages=[page1, page2]), min_bleed_pt=8.5
    )
    assert len(findings) == 1
    assert findings[0].page_num == 2


# ---- B4: page count below economic break-even --------------------------


def test_b4_fires_when_below_min():
    findings = epm_v2_b.detect_b4_page_count_below_min(
        _document(page_count=2), min_pages=4
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_PAGE_COUNT_BELOW_ECONOMIC


def test_b4_quiet_at_min():
    findings = epm_v2_b.detect_b4_page_count_below_min(
        _document(page_count=4), min_pages=4
    )
    assert findings == []


def test_b4_quiet_above_min():
    findings = epm_v2_b.detect_b4_page_count_below_min(
        _document(page_count=10), min_pages=4
    )
    assert findings == []


# ---- B5: image resolution below digital-press min ---------------------


def _ctm(scale_pt: float) -> TransformationMatrix:
    """CTM that scales an image to ``scale_pt`` x ``scale_pt`` points."""
    return TransformationMatrix(a=scale_pt, b=0.0, c=0.0, d=scale_pt, e=0, f=0)


def test_b5_fires_on_low_dpi_image():
    """100x100 px image scaled to 100pt → ~72 DPI, below 200."""
    ev = ImagePlacedEvent(
        operator="Do",
        page_num=1,
        operator_index=0,
        image_name="Im1",
        ctm=_ctm(100.0),
        pixel_width=100,
        pixel_height=100,
    )
    findings = epm_v2_b.detect_b5_image_resolution_below_min(
        events=[ev], min_dpi=200.0
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_IMAGE_RES_BELOW_DIGITAL


def test_b5_quiet_on_high_dpi_image():
    """1000x1000 px image scaled to 100pt → ~720 DPI, above 200."""
    ev = ImagePlacedEvent(
        operator="Do",
        page_num=1,
        operator_index=0,
        image_name="Im1",
        ctm=_ctm(100.0),
        pixel_width=1000,
        pixel_height=1000,
    )
    findings = epm_v2_b.detect_b5_image_resolution_below_min(
        events=[ev], min_dpi=200.0
    )
    assert findings == []


def test_b5_skips_invalid_scale():
    """Zero-scale CTM (degenerate) shouldn't divide by zero."""
    ev = ImagePlacedEvent(
        operator="Do",
        page_num=1,
        operator_index=0,
        image_name="Im1",
        ctm=TransformationMatrix(0.0, 0.0, 0.0, 0.0, 0, 0),
        pixel_width=100,
        pixel_height=100,
    )
    findings = epm_v2_b.detect_b5_image_resolution_below_min(
        events=[ev], min_dpi=200.0
    )
    assert findings == []


def test_b5_dedups_same_image_per_page():
    ev = ImagePlacedEvent(
        operator="Do",
        page_num=1,
        operator_index=0,
        image_name="Im1",
        ctm=_ctm(100.0),
        pixel_width=100,
        pixel_height=100,
    )
    findings = epm_v2_b.detect_b5_image_resolution_below_min(
        events=[ev, ev], min_dpi=200.0
    )
    assert len(findings) == 1


# ---- B6: trim/bleed inconsistent across pages --------------------------


def test_b6_quiet_for_consistent_pages():
    pages = [
        SemanticPage(
            page_num=i + 1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(9, 9, 603, 783),
        )
        for i in range(4)
    ]
    findings = epm_v2_b.detect_b6_trim_inconsistent(
        _document(pages=pages), tolerance_pt=0.5
    )
    assert findings == []


def test_b6_fires_when_trim_varies():
    pages = [
        SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(9, 9, 603, 783),
        ),
        SemanticPage(
            page_num=2,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(20, 20, 580, 760),  # different trim
        ),
    ]
    findings = epm_v2_b.detect_b6_trim_inconsistent(
        _document(pages=pages), tolerance_pt=0.5
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_TRIM_INCONSISTENT


def test_b6_quiet_for_single_page_doc():
    """Single-page docs trivially have consistent geometry."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(9, 9, 603, 783),
    )
    findings = epm_v2_b.detect_b6_trim_inconsistent(
        _document(pages=[page]), tolerance_pt=0.5
    )
    assert findings == []


# ---- EpmTierBAnalyzer end-to-end fan-out -------------------------------


def test_analyzer_fans_out_to_each_tier_b_check():
    pages = [
        SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(0, 0, 612, 792),  # zero bleed → B3
            color_spaces={
                "DeviceCMYK": PdfColorSpace(
                    name="DeviceCMYK", cs_type="DeviceCMYK", components=4,
                ),
                "Spot1": PdfColorSpace(
                    name="Spot1",
                    cs_type="Separation",
                    components=1,
                    colorant_names=("Spot 1",),
                ),
                "Spot2": PdfColorSpace(
                    name="Spot2",
                    cs_type="Separation",
                    components=1,
                    colorant_names=("Spot 2",),
                ),
                "Spot3": PdfColorSpace(
                    name="Spot3",
                    cs_type="Separation",
                    components=1,
                    colorant_names=("Spot 3",),
                ),
                "Spot4": PdfColorSpace(
                    name="Spot4",
                    cs_type="Separation",
                    components=1,
                    colorant_names=("Spot 4",),
                ),
            },
        ),
    ]
    document = _document(pages=pages)  # only 1 page → B4
    events = [
        ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=_ctm(100.0),
            pixel_width=100,
            pixel_height=100,
        ),  # B5
    ]
    analyzer = epm_v2_b.EpmTierBAnalyzer()
    findings = analyzer.analyze(document=document, events=events)
    fired = {f.inspection_id for f in findings}
    assert codes.EPM_BLEED_BELOW_MIN in fired
    assert codes.EPM_PAGE_COUNT_BELOW_ECONOMIC in fired
    assert codes.EPM_IMAGE_RES_BELOW_DIGITAL in fired
    assert codes.EPM_PROCESS_COLOR_COUNT in fired
