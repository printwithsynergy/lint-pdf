"""Tests for TransparencyAnalyzer — blend modes, soft masks, conflicts."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Severity
from grounded.analyzers.transparency import TransparencyAnalyzer
from grounded.semantic.events import (
    ImagePlacedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
)
from grounded.semantic.graphics_state import TransformationMatrix
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestBlendModes:
    """Test GRD_TRANS_001: risky blend mode detection."""

    def test_safe_blend_mode_no_finding(self) -> None:
        event = OpacityChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            blend_mode="Multiply",
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        blend_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_001"]
        assert len(blend_findings) == 0

    def test_risky_blend_mode_delay(self) -> None:
        event = OpacityChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            blend_mode="Difference",
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        blend_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_001"]
        assert len(blend_findings) == 1
        assert blend_findings[0].severity == Severity.SQUALL

    def test_normal_blend_mode_ok(self) -> None:
        event = OpacityChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            blend_mode="Normal",
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        blend_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_001"]
        assert len(blend_findings) == 0

    def test_all_risky_modes(self) -> None:
        """All 8 risky blend modes should trigger findings."""
        risky = [
            "HardLight",
            "SoftLight",
            "Difference",
            "Exclusion",
            "Hue",
            "Saturation",
            "Color",
            "Luminosity",
        ]
        for mode in risky:
            assert TransparencyAnalyzer.is_risky_blend_mode(mode), f"{mode} should be risky"

    def test_all_safe_modes(self) -> None:
        """All 8 safe blend modes should not trigger findings."""
        safe = [
            "Normal",
            "Multiply",
            "Screen",
            "Overlay",
            "Darken",
            "Lighten",
            "ColorDodge",
            "ColorBurn",
        ]
        for mode in safe:
            assert TransparencyAnalyzer.is_safe_blend_mode(mode), f"{mode} should be safe"


class TestTransparencyOverprintConflict:
    """Test GRD_TRANS_002: transparency + overprint conflict."""

    def test_conflict_detected(self) -> None:
        events = [
            OpacityChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                non_stroking_alpha=0.5,
            ),
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=1,
                overprint_stroking=True,
            ),
        ]
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        conflict_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_002"]
        assert len(conflict_findings) == 1
        assert conflict_findings[0].severity == Severity.SQUALL

    def test_no_conflict_without_transparency(self) -> None:
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_stroking=True,
            ),
        ]
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        conflict_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_002"]
        assert len(conflict_findings) == 0

    def test_no_conflict_without_overprint(self) -> None:
        events = [
            OpacityChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                non_stroking_alpha=0.5,
            ),
        ]
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        conflict_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_002"]
        assert len(conflict_findings) == 0


class TestSoftMask:
    """Test GRD_TRANS_003: soft mask detection."""

    def test_soft_mask_advisory(self) -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix.identity(),
            pixel_width=100,
            pixel_height=100,
            has_soft_mask=True,
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mask_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_003"]
        assert len(mask_findings) == 1
        assert mask_findings[0].severity == Severity.ADVISORY

    def test_no_soft_mask_ok(self) -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix.identity(),
            pixel_width=100,
            pixel_height=100,
            has_soft_mask=False,
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mask_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_003"]
        assert len(mask_findings) == 0


class TestTransparencyGroupNonCMYK:
    """Test GRD_TRANS_005: transparency group with non-CMYK color space."""

    def test_rgb_group_advisory(self) -> None:
        """Transparency group with DeviceRGB triggers GRD_TRANS_005."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/CS": "/DeviceRGB"},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        grp_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_005"]
        assert len(grp_findings) == 1
        assert grp_findings[0].severity == Severity.ADVISORY
        assert "DeviceRGB" in grp_findings[0].message

    def test_cmyk_group_no_finding(self) -> None:
        """Transparency group with DeviceCMYK does not trigger GRD_TRANS_005."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/CS": "/DeviceCMYK"},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        grp_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_005"]
        assert len(grp_findings) == 0

    def test_no_group_no_finding(self) -> None:
        """No transparency group does not trigger GRD_TRANS_005."""
        doc = _make_document()
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        grp_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_005"]
        assert len(grp_findings) == 0

    def test_empty_cs_no_finding(self) -> None:
        """Transparency group with empty /CS does not trigger GRD_TRANS_005."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/CS": ""},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        grp_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_005"]
        assert len(grp_findings) == 0


class TestKnockoutTransparencyGroup:
    """Test GRD_TRANS_006: knockout transparency group."""

    def test_knockout_group_advisory(self) -> None:
        """Knockout transparency group triggers GRD_TRANS_006."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/K": True, "/I": False},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        ko_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_006"]
        assert len(ko_findings) == 1
        assert ko_findings[0].severity == Severity.ADVISORY
        assert ko_findings[0].details["knockout"] is True

    def test_non_knockout_group_no_finding(self) -> None:
        """Non-knockout transparency group does not trigger GRD_TRANS_006."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/K": False},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        ko_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_006"]
        assert len(ko_findings) == 0

    def test_no_group_no_knockout_finding(self) -> None:
        """No transparency group does not trigger GRD_TRANS_006."""
        doc = _make_document()
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        ko_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_006"]
        assert len(ko_findings) == 0

    def test_knockout_and_non_cmyk_both_fire(self) -> None:
        """A group with both knockout and non-CMYK triggers both findings."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    transparency_group={"/CS": "/DeviceRGB", "/K": True, "/I": True},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        ids = {f.inspection_id for f in findings}
        assert "GRD_TRANS_005" in ids
        assert "GRD_TRANS_006" in ids


class TestShadingPatternBanding:
    """Test GRD_TRANS_007: shading pattern with banding risk."""

    def test_shading_detected(self) -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    resources={"/Shading": {"Sh1": {"ShadingType": 2}}},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_TRANS_007"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY
        assert f[0].details["shading_count"] == 1

    def test_multiple_shadings(self) -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    resources={
                        "/Shading": {
                            "Sh1": {"ShadingType": 2},
                            "Sh2": {"ShadingType": 3},
                        }
                    },
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_TRANS_007"]
        assert len(f) == 1
        assert f[0].details["shading_count"] == 2

    def test_no_shading_no_flag(self) -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    resources={},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_TRANS_007"]
        assert len(f) == 0

    def test_empty_shading_dict_no_flag(self) -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    resources={"/Shading": {}},
                )
            ],
        )
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_TRANS_007"]
        assert len(f) == 0
