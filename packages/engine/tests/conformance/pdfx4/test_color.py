"""Tests for PDF/X-4 color checks (PDFX4-026-035)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._color import validate_color
from grounded.semantic.events import ColorChangedEvent, TextRenderedEvent
from grounded.semantic.graphics_state import TransformationMatrix
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(
    output_intents: list[dict[str, Any]] | None = None,
    pages: list[SemanticPage] | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        output_intents=output_intents or [],
    )


def _color_event(color_space: str, page_num: int = 1) -> ColorChangedEvent:
    return ColorChangedEvent(
        operator="cs",
        page_num=page_num,
        operator_index=0,
        stroking=False,
        color_space=color_space,
        color_values=(0.0,),
    )


class TestCalibratedProhibited:
    def test_calgray_delay(self) -> None:
        f = validate_color(_doc(), [_color_event("CalGray")])
        ids = [x for x in f if x.inspection_id == "PDFX4-026"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_calrgb_delay(self) -> None:
        f = validate_color(_doc(), [_color_event("CalRGB")])
        ids = [x for x in f if x.inspection_id == "PDFX4-027"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL


class TestDeviceRgb:
    def test_device_rgb_no_intent_delay(self) -> None:
        f = validate_color(_doc(), [_color_event("DeviceRGB")])
        ids = [x for x in f if x.inspection_id == "PDFX4-028"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_device_rgb_with_rgb_intent_ok(self) -> None:
        intent = {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/ColorSpace": "RGB"}}
        f = validate_color(_doc(output_intents=[intent]), [_color_event("DeviceRGB")])
        assert not [x for x in f if x.inspection_id == "PDFX4-028"]

    def test_device_rgb_with_default_rgb_ok(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ColorSpace": {"/DefaultRGB": ["ICCBased", {}]}},
        )
        f = validate_color(_doc(pages=[page]), [_color_event("DeviceRGB")])
        assert not [x for x in f if x.inspection_id == "PDFX4-028"]


class TestDeviceCmyk:
    def test_device_cmyk_no_intent_advisory(self) -> None:
        f = validate_color(_doc(), [_color_event("DeviceCMYK")])
        ids = [x for x in f if x.inspection_id == "PDFX4-029"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    def test_device_cmyk_with_cmyk_intent_ok(self) -> None:
        intent = {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/ColorSpace": "CMYK"}}
        f = validate_color(_doc(output_intents=[intent]), [_color_event("DeviceCMYK")])
        assert not [x for x in f if x.inspection_id == "PDFX4-029"]


class TestDeviceGray:
    def test_device_gray_no_intent_advisory(self) -> None:
        f = validate_color(_doc(), [_color_event("DeviceGray")])
        ids = [x for x in f if x.inspection_id == "PDFX4-030"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestIccBased:
    def test_bad_component_count(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ColorSpace": {"/CS1": ["ICCBased", {"/N": 5}]}},
        )
        f = validate_color(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-031"]
        assert len(ids) == 1

    def test_valid_components_ok(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ColorSpace": {"/CS1": ["ICCBased", {"/N": 4}]}},
        )
        f = validate_color(_doc(pages=[page]), [])
        assert not [x for x in f if x.inspection_id == "PDFX4-031"]


class TestSeparation:
    def test_inconsistent_alternates(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={
                "/ColorSpace": {
                    "/CS1": ["Separation", "PANTONE 123 C", "DeviceCMYK"],
                    "/CS2": ["Separation", "PANTONE 123 C", "DeviceRGB"],
                }
            },
        )
        f = validate_color(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-032"]
        assert len(ids) == 1


class TestDeviceN:
    def test_devicen_advisory(self) -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ColorSpace": {"/CS1": ["DeviceN", ["Cyan", "Magenta"], "DeviceCMYK"]}},
        )
        f = validate_color(_doc(pages=[page]), [])
        ids = [x for x in f if x.inspection_id == "PDFX4-033"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestLab:
    def test_lab_advisory(self) -> None:
        f = validate_color(_doc(), [_color_event("Lab")])
        ids = [x for x in f if x.inspection_id == "PDFX4-034"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestRenderingIntent:
    def test_invalid_rendering_intent(self) -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=12.0,
            ctm=TransformationMatrix.identity(),
            text_matrix=TransformationMatrix.identity(),
            rendering_intent="BadIntent",
        )
        f = validate_color(_doc(), [event])
        ids = [x for x in f if x.inspection_id == "PDFX4-035"]
        assert len(ids) == 1

    def test_valid_rendering_intent_ok(self) -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=12.0,
            ctm=TransformationMatrix.identity(),
            text_matrix=TransformationMatrix.identity(),
            rendering_intent="Perceptual",
        )
        f = validate_color(_doc(), [event])
        assert not [x for x in f if x.inspection_id == "PDFX4-035"]
