"""Tests for the EPM v2 Tier-C analyzer (6 advisory codes)."""

from __future__ import annotations

from siftpdf.analyzers import epm_v2_c
from siftpdf.epm import codes
from siftpdf.semantic.events import PathPaintingEvent
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(*, pages: list[SemanticPage] | None = None, info_dict=None):
    if pages is None:
        pages = [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))]
    return SemanticDocument(
        version="1.7",
        page_count=len(pages),
        is_encrypted=False,
        pages=pages,
        info_dict=info_dict or {},
    )


def _spot(name: str) -> PdfColorSpace:
    return PdfColorSpace(
        name=name,
        cs_type="Separation",
        components=1,
        colorant_names=(name,),
    )


# ---- C1: spot count high (advisory) -----------------------------------


def test_c1_quiet_when_below_cap():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={f"S{i}": _spot(f"PANTONE {i}") for i in range(3)},
    )
    findings = epm_v2_c.detect_c1_spot_count_high(_doc(pages=[page]), advisory_cap=6)
    assert findings == []


def test_c1_fires_when_above_cap():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={f"S{i}": _spot(f"PANTONE {i}") for i in range(8)},
    )
    findings = epm_v2_c.detect_c1_spot_count_high(_doc(pages=[page]), advisory_cap=6)
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_SPOT_COUNT_HIGH


# ---- C2: feature below digital-press resolution -----------------------


def test_c2_fires_on_thin_stroke():
    ev = PathPaintingEvent(
        operator="S",
        page_num=1,
        operator_index=0,
        fill=False,
        stroke=True,
        line_width=0.1,
    )
    findings = epm_v2_c.detect_c2_feature_below_digital_res(events=[ev], min_line_weight_pt=0.35)
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_FEATURE_BELOW_DIGITAL_RES


def test_c2_quiet_on_above_min():
    ev = PathPaintingEvent(
        operator="S",
        page_num=1,
        operator_index=0,
        fill=False,
        stroke=True,
        line_width=1.0,
    )
    findings = epm_v2_c.detect_c2_feature_below_digital_res(events=[ev], min_line_weight_pt=0.35)
    assert findings == []


def test_c2_skips_unstroked_paths():
    ev = PathPaintingEvent(
        operator="f",
        page_num=1,
        operator_index=0,
        fill=True,
        stroke=False,
        line_width=0.1,
    )
    findings = epm_v2_c.detect_c2_feature_below_digital_res(events=[ev], min_line_weight_pt=0.35)
    assert findings == []


# ---- C3: mixed process color spaces -----------------------------------


def test_c3_fires_on_cmyk_plus_separation_mix():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={
            "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
            "Spot": _spot("Spot"),
        },
    )
    findings = epm_v2_c.detect_c3_mixed_process_spaces(_doc(pages=[page]))
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_MIXED_PROCESS_SPACES


def test_c3_quiet_for_pure_cmyk():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={
            "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
        },
    )
    findings = epm_v2_c.detect_c3_mixed_process_spaces(_doc(pages=[page]))
    assert findings == []


# ---- C5: trapping disabled --------------------------------------------


def test_c5_fires_when_trapped_missing():
    findings = epm_v2_c.detect_c5_trapping_disabled(_doc(info_dict={}))
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_TRAPPING_DISABLED


def test_c5_fires_when_trapped_unknown():
    findings = epm_v2_c.detect_c5_trapping_disabled(_doc(info_dict={"/Trapped": "Unknown"}))
    assert len(findings) == 1


def test_c5_quiet_when_trapped_true():
    findings = epm_v2_c.detect_c5_trapping_disabled(_doc(info_dict={"/Trapped": "True"}))
    assert findings == []


# ---- C6: trim/bleed mis-aligned ---------------------------------------


def test_c6_fires_when_trim_off_centre():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        # 0pt margin on left, 30pt on right → off-centre
        trim_box=PdfBox(0, 9, 582, 783),
    )
    findings = epm_v2_c.detect_c6_trim_bleed_misaligned(_doc(pages=[page]), tolerance_pt=1.0)
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_TRIM_BLEED_MISALIGNED


def test_c6_quiet_when_centred():
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        bleed_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(9, 9, 603, 783),  # 9pt all sides, centred
    )
    findings = epm_v2_c.detect_c6_trim_bleed_misaligned(_doc(pages=[page]), tolerance_pt=1.0)
    assert findings == []


# ---- C7: page geometry varies -----------------------------------------


def test_c7_fires_when_page_sizes_vary():
    pages = [
        SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)),
        SemanticPage(page_num=2, media_box=PdfBox(0, 0, 595, 842)),
    ]
    findings = epm_v2_c.detect_c7_page_geometry_varies(_doc(pages=pages))
    assert len(findings) == 1
    assert findings[0].inspection_id == codes.EPM_PAGE_GEOMETRY_VARIES


def test_c7_quiet_for_uniform_sizes():
    pages = [SemanticPage(page_num=i + 1, media_box=PdfBox(0, 0, 612, 792)) for i in range(3)]
    findings = epm_v2_c.detect_c7_page_geometry_varies(_doc(pages=pages))
    assert findings == []


def test_c7_quiet_for_single_page():
    findings = epm_v2_c.detect_c7_page_geometry_varies(
        _doc(pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))])
    )
    assert findings == []


# ---- EpmTierCAnalyzer end-to-end fan-out ------------------------------


def test_analyzer_fans_out_to_each_tier_c_check():
    pages = [
        SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(0, 9, 582, 783),  # off-centre → C6
            color_spaces={
                "DeviceCMYK": PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4),
                "Spot": _spot("Spot"),  # mix → C3
            },
        ),
        SemanticPage(
            page_num=2,
            media_box=PdfBox(0, 0, 595, 842),  # different size → C7
        ),
    ]
    document = _doc(pages=pages, info_dict={})  # no Trapped → C5
    events = [
        PathPaintingEvent(
            operator="S",
            page_num=1,
            operator_index=0,
            fill=False,
            stroke=True,
            line_width=0.1,
        ),  # C2
    ]
    analyzer = epm_v2_c.EpmTierCAnalyzer()
    findings = analyzer.analyze(document=document, events=events)
    fired = {f.inspection_id for f in findings}
    assert codes.EPM_FEATURE_BELOW_DIGITAL_RES in fired
    assert codes.EPM_MIXED_PROCESS_SPACES in fired
    assert codes.EPM_TRAPPING_DISABLED in fired
    assert codes.EPM_TRIM_BLEED_MISALIGNED in fired
    assert codes.EPM_PAGE_GEOMETRY_VARIES in fired


def test_score_walks_tier_c_findings_as_advisories():
    """Integration smoke: scorer treats C-tier as advisories, not rejection."""
    from siftpdf.epm.scoring import EpmTier, score_epm_candidacy

    fired = [codes.EPM_TRAPPING_DISABLED, codes.EPM_FEATURE_BELOW_DIGITAL_RES]
    verdict = score_epm_candidacy(fired)
    assert verdict.tier == EpmTier.PASS_WITH_ADVISORY
    for code in fired:
        assert code in verdict.advisories
