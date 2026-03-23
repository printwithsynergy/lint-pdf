"""Tests for TransparencyAnalyzer — blend modes, soft masks, conflicts."""

from __future__ import annotations

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

    @staticmethod
    def test_safe_blend_mode_no_finding() -> None:
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

    @staticmethod
    def test_risky_blend_mode_delay() -> None:
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
        assert blend_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_normal_blend_mode_ok() -> None:
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

    @staticmethod
    def test_all_risky_modes() -> None:
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

    @staticmethod
    def test_all_safe_modes() -> None:
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

    @staticmethod
    def test_conflict_detected() -> None:
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
        assert conflict_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_no_conflict_without_transparency() -> None:
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

    @staticmethod
    def test_no_conflict_without_overprint() -> None:
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

    @staticmethod
    def test_soft_mask_advisory() -> None:
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

    @staticmethod
    def test_no_soft_mask_ok() -> None:
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

    @staticmethod
    def test_rgb_group_advisory() -> None:
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

    @staticmethod
    def test_cmyk_group_no_finding() -> None:
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

    @staticmethod
    def test_no_group_no_finding() -> None:
        """No transparency group does not trigger GRD_TRANS_005."""
        doc = _make_document()
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        grp_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_005"]
        assert len(grp_findings) == 0

    @staticmethod
    def test_empty_cs_no_finding() -> None:
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

    @staticmethod
    def test_knockout_group_advisory() -> None:
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

    @staticmethod
    def test_non_knockout_group_no_finding() -> None:
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

    @staticmethod
    def test_no_group_no_knockout_finding() -> None:
        """No transparency group does not trigger GRD_TRANS_006."""
        doc = _make_document()
        analyzer = TransparencyAnalyzer()
        findings = analyzer.analyze(doc, [])
        ko_findings = [f for f in findings if f.inspection_id == "GRD_TRANS_006"]
        assert len(ko_findings) == 0

    @staticmethod
    def test_knockout_and_non_cmyk_both_fire() -> None:
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

    @staticmethod
    def test_shading_detected() -> None:
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

    @staticmethod
    def test_multiple_shadings() -> None:
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

    @staticmethod
    def test_no_shading_no_flag() -> None:
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

    @staticmethod
    def test_empty_shading_dict_no_flag() -> None:
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
