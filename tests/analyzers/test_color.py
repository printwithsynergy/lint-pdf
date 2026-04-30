"""Tests for ColorAnalyzer — TAC, prohibited spaces, ICC validation."""

from __future__ import annotations

from lintpdf.analyzers.color import ColorAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.events import (
    ColorChangedEvent,
    OverprintChangedEvent,
    PathPaintingEvent,
    TextRenderedEvent,
)
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _make_document(
    color_spaces: dict[str, PdfColorSpace] | None = None,
) -> SemanticDocument:
    """Minimal document with optional color spaces."""
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                color_spaces=color_spaces or {},
            )
        ],
    )


class TestTACCalculation:
    """Test LPDF_COLOR_004: TAC calculation."""

    @staticmethod
    def test_tac_within_limit() -> None:
        """C=50% M=40% Y=40% K=20% = 150% TAC — within 300% limit."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.5, 0.4, 0.4, 0.2),
        )
        analyzer = ColorAnalyzer(tac_limit=300)
        findings = analyzer.analyze(_make_document(), [event])
        tac_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_004"]
        assert len(tac_findings) == 0

    @staticmethod
    def test_tac_exceeds_limit() -> None:
        """C=100% M=80% Y=70% K=100% = 350% TAC — exceeds 300%."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(1.0, 0.8, 0.7, 1.0),
        )
        analyzer = ColorAnalyzer(tac_limit=300)
        findings = analyzer.analyze(_make_document(), [event])
        tac_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_004"]
        assert len(tac_findings) == 1
        assert tac_findings[0].severity == Severity.WARNING
        assert tac_findings[0].details["tac"] == 350.0

    @staticmethod
    def test_tac_stroke_color() -> None:
        """TAC check also applies to stroke colors."""
        event = PathPaintingEvent(
            operator="S",
            page_num=1,
            operator_index=0,
            fill=False,
            stroke=True,
            stroke_color_space="DeviceCMYK",
            stroke_color_values=(1.0, 1.0, 1.0, 1.0),
        )
        analyzer = ColorAnalyzer(tac_limit=300)
        findings = analyzer.analyze(_make_document(), [event])
        tac_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_004"]
        assert len(tac_findings) == 1
        assert tac_findings[0].details["tac"] == 400.0

    @staticmethod
    def test_tac_non_cmyk_ignored() -> None:
        """TAC check only applies to DeviceCMYK."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceRGB",
            fill_color_values=(1.0, 1.0, 1.0),
        )
        analyzer = ColorAnalyzer(tac_limit=300)
        findings = analyzer.analyze(_make_document(), [event])
        tac_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_004"]
        assert len(tac_findings) == 0

    @staticmethod
    def test_configurable_tac_limit() -> None:
        """TAC limit is configurable (web offset = 260%)."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.8, 0.7, 0.6, 0.5),  # 260% TAC
        )
        # Within 300% limit
        analyzer_300 = ColorAnalyzer(tac_limit=300)
        assert (
            len(
                [
                    f
                    for f in analyzer_300.analyze(_make_document(), [event])
                    if f.inspection_id == "LPDF_COLOR_004"
                ]
            )
            == 0
        )

        # Exceeds 250% limit
        analyzer_250 = ColorAnalyzer(tac_limit=250)
        assert (
            len(
                [
                    f
                    for f in analyzer_250.analyze(_make_document(), [event])
                    if f.inspection_id == "LPDF_COLOR_004"
                ]
            )
            == 1
        )


class TestProhibitedSpaces:
    """Test LPDF_COLOR_001: prohibited color spaces."""

    @staticmethod
    def test_calgray_prohibited() -> None:
        event = ColorChangedEvent(
            operator="cs",
            page_num=1,
            operator_index=0,
            stroking=False,
            color_space="CalGray",
            color_values=(0.5,),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        prohibited = [f for f in findings if f.inspection_id == "LPDF_COLOR_001"]
        assert len(prohibited) == 1
        assert prohibited[0].severity == Severity.ERROR

    @staticmethod
    def test_calrgb_prohibited() -> None:
        event = ColorChangedEvent(
            operator="cs",
            page_num=1,
            operator_index=0,
            stroking=False,
            color_space="CalRGB",
            color_values=(0.5, 0.5, 0.5),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        prohibited = [f for f in findings if f.inspection_id == "LPDF_COLOR_001"]
        assert len(prohibited) == 1

    @staticmethod
    def test_device_cmyk_not_prohibited() -> None:
        event = ColorChangedEvent(
            operator="k",
            page_num=1,
            operator_index=0,
            stroking=False,
            color_space="DeviceCMYK",
            color_values=(0.0, 0.0, 0.0, 1.0),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        prohibited = [f for f in findings if f.inspection_id == "LPDF_COLOR_001"]
        assert len(prohibited) == 0

    @staticmethod
    def test_prohibited_from_page_resources() -> None:
        """Prohibited spaces detected in page resource definitions."""
        doc = _make_document(
            color_spaces={
                "CS1": PdfColorSpace(name="CS1", cs_type="CalRGB", components=3),
            }
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        prohibited = [f for f in findings if f.inspection_id == "LPDF_COLOR_001"]
        assert len(prohibited) == 1


class TestDeviceRGBWithoutICC:
    """Test LPDF_COLOR_002: DeviceRGB without ICC profile."""

    @staticmethod
    def test_device_rgb_no_icc() -> None:
        doc = _make_document(
            color_spaces={
                "DefaultRGB": PdfColorSpace(
                    name="DefaultRGB",
                    cs_type="DeviceRGB",
                    components=3,
                    icc_profile_ref=None,
                ),
            }
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        rgb_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_002"]
        assert len(rgb_findings) == 1
        assert rgb_findings[0].severity == Severity.WARNING


class TestSpotColorBacking:
    """Test LPDF_COLOR_003: spot color without alternate."""

    @staticmethod
    def test_separation_no_alternate() -> None:
        doc = _make_document(
            color_spaces={
                "Pantone123": PdfColorSpace(
                    name="Pantone123",
                    cs_type="Separation",
                    components=1,
                    alternate=None,
                ),
            }
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        spot_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_003"]
        assert len(spot_findings) == 1

    @staticmethod
    def test_separation_with_alternate_ok() -> None:
        doc = _make_document(
            color_spaces={
                "Pantone123": PdfColorSpace(
                    name="Pantone123",
                    cs_type="Separation",
                    components=1,
                    alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
                ),
            }
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        spot_findings = [f for f in findings if f.inspection_id == "LPDF_COLOR_003"]
        assert len(spot_findings) == 0


class TestRichBlackText:
    """Test LPDF_COLOR_008: rich black on small text."""

    def _text_event(
        self,
        font_size: float = 10.0,
        color_values: tuple[float, ...] = (0.4, 0.3, 0.2, 1.0),
        color_space: str = "DeviceCMYK",
    ) -> TextRenderedEvent:
        return TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=font_size,
            ctm=TransformationMatrix.identity(),
            text_matrix=TransformationMatrix.identity(),
            color_space=color_space,
            color_values=color_values,
        )

    def test_rich_black_small_text(self) -> None:
        """10pt CMYK text with >1 ink triggers LPDF_COLOR_008."""
        event = self._text_event(font_size=10.0, color_values=(0.4, 0.3, 0.2, 1.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_008"]
        assert len(rb) == 1
        assert rb[0].severity == Severity.WARNING

    def test_large_text_no_rich_black_finding(self) -> None:
        """14pt text is above 12pt threshold — no LPDF_COLOR_008."""
        event = self._text_event(font_size=14.0, color_values=(0.4, 0.3, 0.2, 1.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_008"]
        assert len(rb) == 0

    def test_single_ink_no_finding(self) -> None:
        """K-only text does not trigger LPDF_COLOR_008."""
        event = self._text_event(font_size=10.0, color_values=(0.0, 0.0, 0.0, 1.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_008"]
        assert len(rb) == 0

    def test_rgb_text_no_finding(self) -> None:
        """Non-CMYK text does not trigger LPDF_COLOR_008."""
        event = self._text_event(
            font_size=10.0, color_space="DeviceRGB", color_values=(0.0, 0.0, 0.0)
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_008"]
        assert len(rb) == 0

    def test_rich_black_details(self) -> None:
        event = self._text_event(font_size=8.0, color_values=(0.3, 0.2, 0.1, 1.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        rb = next((f for f in findings if f.inspection_id == "LPDF_COLOR_008"), None)
        assert rb is not None
        assert rb.details["non_zero_inks"] == 4
        assert rb.object_type == "text"


class TestKnockoutBlack:
    """Test LPDF_COLOR_009: 100% K fill without overprint."""

    def _fill_event(
        self,
        fill_values: tuple[float, ...] = (0.0, 0.0, 0.0, 1.0),
        fill_cs: str = "DeviceCMYK",
    ) -> PathPaintingEvent:
        return PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=5,
            fill=True,
            stroke=False,
            fill_color_space=fill_cs,
            fill_color_values=fill_values,
        )

    def test_knockout_black_advisory(self) -> None:
        """Pure 100% K fill without overprint triggers LPDF_COLOR_009.

        WS-7 gates this rule on ``brand_palette_present`` since the
        "was the pure-K intentional?" question is only answerable
        against a brand rich-black spec; the test opts in.
        """
        event = self._fill_event()
        analyzer = ColorAnalyzer(brand_palette_present=True)
        findings = analyzer.analyze(_make_document(), [event])
        ko = [f for f in findings if f.inspection_id == "LPDF_COLOR_009"]
        assert len(ko) == 1
        assert ko[0].severity == Severity.ADVISORY

    def test_with_overprint_no_finding(self) -> None:
        """100% K fill with overprint ON does not trigger LPDF_COLOR_009."""
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_non_stroking=True,
            ),
            self._fill_event(),
        ]
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        ko = [f for f in findings if f.inspection_id == "LPDF_COLOR_009"]
        assert len(ko) == 0

    def test_rich_black_no_knockout_finding(self) -> None:
        """Rich black fill (C>0) does not trigger LPDF_COLOR_009."""
        event = self._fill_event(fill_values=(0.4, 0.3, 0.2, 1.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        ko = [f for f in findings if f.inspection_id == "LPDF_COLOR_009"]
        assert len(ko) == 0

    def test_non_cmyk_no_finding(self) -> None:
        """Non-CMYK fill does not trigger LPDF_COLOR_009."""
        event = self._fill_event(fill_cs="DeviceRGB", fill_values=(0.0, 0.0, 0.0))
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        ko = [f for f in findings if f.inspection_id == "LPDF_COLOR_009"]
        assert len(ko) == 0


class TestPureKFill:
    """Test LPDF_COLOR_010: pure K-only on large fill."""

    @staticmethod
    def test_pure_k_fill_advisory() -> None:
        """80% K-only fill triggers LPDF_COLOR_010.

        WS-7 gates on ``brand_palette_present`` (ambiguous without
        a brand rich-black spec) and aggregates per page; the
        payload now carries ``max_k_percent`` + ``object_count``.
        """
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.0, 0.0, 0.0, 0.8),
        )
        analyzer = ColorAnalyzer(brand_palette_present=True)
        findings = analyzer.analyze(_make_document(), [event])
        pk = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
        assert len(pk) == 1
        assert pk[0].severity == Severity.ADVISORY
        assert pk[0].details["max_k_percent"] == 80.0
        assert pk[0].details["object_count"] == 1

    @staticmethod
    def test_low_k_no_finding() -> None:
        """40% K-only fill does not trigger (below 50% threshold)."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.0, 0.0, 0.0, 0.4),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        pk = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
        assert len(pk) == 0

    @staticmethod
    def test_rich_black_no_pure_k_finding() -> None:
        """Rich black fill does not trigger LPDF_COLOR_010."""
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=0,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.4, 0.3, 0.2, 1.0),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        pk = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
        assert len(pk) == 0

    @staticmethod
    def test_stroke_only_no_finding() -> None:
        """K-only stroke (not fill) does not trigger LPDF_COLOR_010."""
        event = PathPaintingEvent(
            operator="S",
            page_num=1,
            operator_index=0,
            fill=False,
            stroke=True,
            stroke_color_space="DeviceCMYK",
            stroke_color_values=(0.0, 0.0, 0.0, 0.8),
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        pk = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
        assert len(pk) == 0


class TestSpotColorConflicts:
    """Test LPDF_COLOR_011: spot color name conflict detection."""

    @staticmethod
    def test_conflicting_alternates() -> None:
        """Same colorant with different alternates triggers LPDF_COLOR_011."""
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces={
                        "CS1": PdfColorSpace(
                            name="CS1",
                            cs_type="Separation",
                            components=1,
                            colorant_names=("PANTONE 485 C",),
                            alternate=PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4),
                        ),
                    },
                ),
                SemanticPage(
                    page_num=2,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces={
                        "CS2": PdfColorSpace(
                            name="CS2",
                            cs_type="Separation",
                            components=1,
                            colorant_names=("PANTONE 485 C",),
                            alternate=PdfColorSpace(name=None, cs_type="DeviceRGB", components=3),
                        ),
                    },
                ),
            ],
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        sc = [f for f in findings if f.inspection_id == "LPDF_COLOR_011"]
        assert len(sc) == 1
        assert sc[0].severity == Severity.WARNING
        assert "PANTONE 485 C" in sc[0].message

    @staticmethod
    def test_same_alternates_no_conflict() -> None:
        """Same colorant with same alternate does not trigger LPDF_COLOR_011."""
        alt = PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4)
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces={
                        "CS1": PdfColorSpace(
                            name="CS1",
                            cs_type="Separation",
                            components=1,
                            colorant_names=("PANTONE 485 C",),
                            alternate=alt,
                        ),
                    },
                ),
                SemanticPage(
                    page_num=2,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces={
                        "CS2": PdfColorSpace(
                            name="CS2",
                            cs_type="Separation",
                            components=1,
                            colorant_names=("PANTONE 485 C",),
                            alternate=alt,
                        ),
                    },
                ),
            ],
        )
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        sc = [f for f in findings if f.inspection_id == "LPDF_COLOR_011"]
        assert len(sc) == 0

    @staticmethod
    def test_no_spots_no_conflict() -> None:
        """Document with no spot colors does not trigger LPDF_COLOR_011."""
        doc = _make_document()
        analyzer = ColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        sc = [f for f in findings if f.inspection_id == "LPDF_COLOR_011"]
        assert len(sc) == 0
