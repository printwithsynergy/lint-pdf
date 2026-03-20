"""Tests for HairlineAnalyzer — GRD_TEXT_003-006 (Part 4 deepening).

Tests invisible text, white text, registration text, and small multi-ink text.
"""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Severity
from grounded.analyzers.hairline import HairlineAnalyzer
from grounded.semantic.events import TextRenderedEvent
from grounded.semantic.graphics_state import TransformationMatrix
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _text_event(
    font_size: float = 12.0,
    color_space: str = "DeviceGray",
    color_values: tuple[float, ...] = (0.0,),
    rendering_mode: int = 0,
    page_num: int = 1,
    ctm_scale: float = 1.0,
    tm_scale: float = 1.0,
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        ctm=TransformationMatrix(a=ctm_scale, d=ctm_scale),
        text_matrix=TransformationMatrix(a=tm_scale, d=tm_scale),
        color_space=color_space,
        color_values=color_values,
        rendering_mode=rendering_mode,
    )


class TestInvisibleText:
    """Test GRD_TEXT_003: invisible text (rendering mode 3)."""

    def test_invisible_text_advisory(self) -> None:
        """Rendering mode 3 triggers GRD_TEXT_003."""
        event = _text_event(rendering_mode=3)
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        inv = [f for f in findings if f.inspection_id == "GRD_TEXT_003"]
        assert len(inv) == 1
        assert inv[0].severity == Severity.ADVISORY
        assert inv[0].object_type == "text"

    def test_visible_text_no_finding(self) -> None:
        """Rendering mode 0 (normal fill) does not trigger GRD_TEXT_003."""
        event = _text_event(rendering_mode=0)
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        inv = [f for f in findings if f.inspection_id == "GRD_TEXT_003"]
        assert len(inv) == 0

    def test_stroke_text_no_finding(self) -> None:
        """Rendering mode 1 (stroke) does not trigger GRD_TEXT_003."""
        event = _text_event(rendering_mode=1)
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        inv = [f for f in findings if f.inspection_id == "GRD_TEXT_003"]
        assert len(inv) == 0

    def test_invisible_text_details(self) -> None:
        event = _text_event(rendering_mode=3)
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        inv = next((f for f in findings if f.inspection_id == "GRD_TEXT_003"), None)
        assert inv is not None
        assert inv.details["rendering_mode"] == 3
        assert inv.details["font_name"] == "F1"


class TestWhiteText:
    """Test GRD_TEXT_004: white text detection."""

    def test_white_gray_text(self) -> None:
        """DeviceGray 1.0 triggers GRD_TEXT_004."""
        event = _text_event(color_space="DeviceGray", color_values=(1.0,))
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert len(wt) == 1
        assert wt[0].severity == Severity.ADVISORY

    def test_white_rgb_text(self) -> None:
        """DeviceRGB 1,1,1 triggers GRD_TEXT_004."""
        event = _text_event(color_space="DeviceRGB", color_values=(1.0, 1.0, 1.0))
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert len(wt) == 1

    def test_white_cmyk_text(self) -> None:
        """DeviceCMYK 0,0,0,0 triggers GRD_TEXT_004."""
        event = _text_event(color_space="DeviceCMYK", color_values=(0.0, 0.0, 0.0, 0.0))
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert len(wt) == 1

    def test_black_text_no_finding(self) -> None:
        """Black text does not trigger GRD_TEXT_004."""
        event = _text_event(color_space="DeviceGray", color_values=(0.0,))
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert len(wt) == 0

    def test_dark_gray_no_finding(self) -> None:
        """Dark gray text (0.5) does not trigger GRD_TEXT_004."""
        event = _text_event(color_space="DeviceGray", color_values=(0.5,))
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert len(wt) == 0

    def test_white_text_page_num(self) -> None:
        event = _text_event(color_space="DeviceGray", color_values=(1.0,), page_num=5)
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        wt = [f for f in findings if f.inspection_id == "GRD_TEXT_004"]
        assert wt[0].page_num == 5


class TestRegistrationText:
    """Test GRD_TEXT_005: text on registration color."""

    def test_registration_text_delay(self) -> None:
        """All CMYK at 100% triggers GRD_TEXT_005."""
        event = _text_event(
            color_space="DeviceCMYK",
            color_values=(1.0, 1.0, 1.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        reg = [f for f in findings if f.inspection_id == "GRD_TEXT_005"]
        assert len(reg) == 1
        assert reg[0].severity == Severity.SQUALL

    def test_near_registration_triggers(self) -> None:
        """Near-100% values (within tolerance) trigger GRD_TEXT_005."""
        event = _text_event(
            color_space="DeviceCMYK",
            color_values=(0.995, 1.0, 0.998, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        reg = [f for f in findings if f.inspection_id == "GRD_TEXT_005"]
        assert len(reg) == 1

    def test_black_only_no_registration(self) -> None:
        """100% K only does not trigger GRD_TEXT_005."""
        event = _text_event(
            color_space="DeviceCMYK",
            color_values=(0.0, 0.0, 0.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        reg = [f for f in findings if f.inspection_id == "GRD_TEXT_005"]
        assert len(reg) == 0

    def test_rgb_text_no_registration(self) -> None:
        """Non-CMYK text does not trigger GRD_TEXT_005."""
        event = _text_event(
            color_space="DeviceRGB",
            color_values=(0.0, 0.0, 0.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        reg = [f for f in findings if f.inspection_id == "GRD_TEXT_005"]
        assert len(reg) == 0

    def test_registration_text_details(self) -> None:
        event = _text_event(
            color_space="DeviceCMYK",
            color_values=(1.0, 1.0, 1.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        reg = next((f for f in findings if f.inspection_id == "GRD_TEXT_005"), None)
        assert reg is not None
        assert reg.details["font_name"] == "F1"
        assert reg.object_type == "text"


class TestSmallMultiInkText:
    """Test GRD_TEXT_006: small multi-ink text."""

    def test_small_multi_ink_delay(self) -> None:
        """7pt CMYK text with >1 ink triggers GRD_TEXT_006."""
        event = _text_event(
            font_size=7.0,
            color_space="DeviceCMYK",
            color_values=(0.4, 0.3, 0.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = [f for f in findings if f.inspection_id == "GRD_TEXT_006"]
        assert len(mi) == 1
        assert mi[0].severity == Severity.SQUALL

    def test_large_multi_ink_no_finding(self) -> None:
        """10pt CMYK text with >1 ink does not trigger GRD_TEXT_006 (above 8pt)."""
        event = _text_event(
            font_size=10.0,
            color_space="DeviceCMYK",
            color_values=(0.4, 0.3, 0.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = [f for f in findings if f.inspection_id == "GRD_TEXT_006"]
        assert len(mi) == 0

    def test_small_single_ink_no_finding(self) -> None:
        """7pt K-only text does not trigger GRD_TEXT_006."""
        event = _text_event(
            font_size=7.0,
            color_space="DeviceCMYK",
            color_values=(0.0, 0.0, 0.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = [f for f in findings if f.inspection_id == "GRD_TEXT_006"]
        assert len(mi) == 0

    def test_small_rgb_no_finding(self) -> None:
        """Small RGB text does not trigger GRD_TEXT_006 (not CMYK)."""
        event = _text_event(
            font_size=6.0,
            color_space="DeviceRGB",
            color_values=(0.5, 0.3, 0.2),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = [f for f in findings if f.inspection_id == "GRD_TEXT_006"]
        assert len(mi) == 0

    def test_effective_size_with_scaling(self) -> None:
        """12pt text scaled down to 6pt effective triggers GRD_TEXT_006."""
        event = _text_event(
            font_size=12.0,
            ctm_scale=0.5,
            color_space="DeviceCMYK",
            color_values=(0.4, 0.3, 0.0, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = [f for f in findings if f.inspection_id == "GRD_TEXT_006"]
        assert len(mi) == 1

    def test_multi_ink_details(self) -> None:
        event = _text_event(
            font_size=6.0,
            color_space="DeviceCMYK",
            color_values=(0.3, 0.2, 0.1, 1.0),
        )
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        mi = next((f for f in findings if f.inspection_id == "GRD_TEXT_006"), None)
        assert mi is not None
        assert mi.details["non_zero_inks"] == 4
        assert mi.details["effective_size"] < 8.0
