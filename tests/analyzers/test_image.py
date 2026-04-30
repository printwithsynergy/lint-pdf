"""Tests for ImageAnalyzer — DPI calculation and image checks."""

from __future__ import annotations

import math

from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.image import ImageAnalyzer
from siftpdf.semantic.events import ImagePlacedEvent
from siftpdf.semantic.graphics_state import TransformationMatrix
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_image_event(
    pixel_width: int = 1000,
    pixel_height: int = 800,
    ctm: TransformationMatrix | None = None,
    color_space: str = "DeviceRGB",
    filters: tuple[str, ...] = (),
    is_inline: bool = False,
    has_soft_mask: bool = False,
    page_num: int = 1,
    image_name: str = "Im1",
) -> ImagePlacedEvent:
    """Helper to create ImagePlacedEvent."""
    if ctm is None:
        ctm = TransformationMatrix(a=200, b=0, c=0, d=300, e=100, f=400)
    return ImagePlacedEvent(
        operator="Do",
        page_num=page_num,
        operator_index=0,
        image_name=image_name,
        ctm=ctm,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        color_space=color_space,
        filters=filters,
        has_soft_mask=has_soft_mask,
        is_inline=is_inline,
    )


def _make_document() -> SemanticDocument:
    """Minimal SemanticDocument for analyzer."""
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
            )
        ],
    )


class TestDPICalculation:
    """Test effective DPI calculation from CTM."""

    @staticmethod
    def test_known_dpi() -> None:
        """200pt wide display for 1000px image = 360 DPI."""
        event = _make_image_event(
            pixel_width=1000,
            pixel_height=800,
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert result.is_valid
        # dpi_x = 1000 / (200/72) = 1000 / 2.778 = 360
        assert abs(result.dpi_x - 360.0) < 0.1
        # dpi_y = 800 / (300/72) = 800 / 4.167 = 192
        assert abs(result.dpi_y - 192.0) < 0.1
        assert result.dpi_effective == min(result.dpi_x, result.dpi_y)

    @staticmethod
    def test_identity_matrix_dpi() -> None:
        """Identity CTM: 1pt display. 100px image = 7200 DPI."""
        event = _make_image_event(
            pixel_width=100,
            pixel_height=100,
            ctm=TransformationMatrix.identity(),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert result.is_valid
        assert abs(result.dpi_x - 7200.0) < 0.1
        assert abs(result.dpi_y - 7200.0) < 0.1

    @staticmethod
    def test_rotated_image_dpi() -> None:
        """90-degree rotation: a=0, b=300, c=-200, d=0."""
        event = _make_image_event(
            pixel_width=1000,
            pixel_height=800,
            ctm=TransformationMatrix(a=0, b=300, c=-200, d=0, e=0, f=0),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert result.is_valid
        # sx = sqrt(0^2 + (-200)^2) = 200
        # sy = sqrt(300^2 + 0^2) = 300
        assert abs(result.dpi_x - 360.0) < 0.1
        assert abs(result.dpi_y - 192.0) < 0.1

    @staticmethod
    def test_degenerate_ctm() -> None:
        """Zero-scale CTM should return invalid."""
        event = _make_image_event(
            ctm=TransformationMatrix(a=0, b=0, c=0, d=0, e=100, f=200),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert not result.is_valid
        assert result.dpi_x == float("inf")

    @staticmethod
    def test_scaled_image() -> None:
        """72pt display = 1 inch. 300px = 300 DPI."""
        event = _make_image_event(
            pixel_width=300,
            pixel_height=300,
            ctm=TransformationMatrix(a=72, b=0, c=0, d=72, e=0, f=0),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert result.is_valid
        assert abs(result.dpi_x - 300.0) < 0.1
        assert abs(result.dpi_y - 300.0) < 0.1

    @staticmethod
    def test_skewed_image() -> None:
        """Skew matrix: a=100, b=50, c=30, d=200."""
        event = _make_image_event(
            pixel_width=500,
            pixel_height=500,
            ctm=TransformationMatrix(a=100, b=50, c=30, d=200, e=0, f=0),
        )
        result = ImageAnalyzer.calculate_dpi(event)
        assert result.is_valid
        sx = math.sqrt(100**2 + 30**2)
        sy = math.sqrt(50**2 + 200**2)
        expected_dpi_x = 500 / (sx / 72)
        expected_dpi_y = 500 / (sy / 72)
        assert abs(result.dpi_x - expected_dpi_x) < 0.1
        assert abs(result.dpi_y - expected_dpi_y) < 0.1


class TestImageAnalyzerFindings:
    """Test ImageAnalyzer finding generation."""

    @staticmethod
    def test_low_dpi_finding() -> None:
        """Image below min DPI threshold triggers LPDF_IMG_001."""
        # 72pt display, 100px = 100 DPI (below 150 default)
        event = _make_image_event(
            pixel_width=100,
            pixel_height=100,
            ctm=TransformationMatrix(a=72, b=0, c=0, d=72, e=0, f=0),
        )
        analyzer = ImageAnalyzer(min_dpi=150)
        findings = analyzer.analyze(_make_document(), [event])
        img_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_001"]
        assert len(img_findings) == 1
        assert img_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_excessive_dpi_finding() -> None:
        """Image above max DPI threshold triggers LPDF_IMG_002."""
        # 72pt display, 1000px = 1000 DPI (above 600 default)
        event = _make_image_event(
            pixel_width=1000,
            pixel_height=1000,
            ctm=TransformationMatrix(a=72, b=0, c=0, d=72, e=0, f=0),
        )
        analyzer = ImageAnalyzer(max_dpi=600)
        findings = analyzer.analyze(_make_document(), [event])
        img_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_002"]
        assert len(img_findings) == 1
        assert img_findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_acceptable_dpi_no_finding() -> None:
        """Image within range generates no DPI findings."""
        # 72pt display, 300px = 300 DPI
        event = _make_image_event(
            pixel_width=300,
            pixel_height=300,
            ctm=TransformationMatrix(a=72, b=0, c=0, d=72, e=0, f=0),
        )
        analyzer = ImageAnalyzer(min_dpi=150, max_dpi=600)
        findings = analyzer.analyze(_make_document(), [event])
        dpi_findings = [f for f in findings if f.inspection_id in ("LPDF_IMG_001", "LPDF_IMG_002")]
        assert len(dpi_findings) == 0

    @staticmethod
    def test_no_compression_finding() -> None:
        """ASCII-only filter triggers LPDF_IMG_004."""
        event = _make_image_event(filters=("ASCIIHexDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        comp_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_004"]
        assert len(comp_findings) == 1

    @staticmethod
    def test_real_compression_no_finding() -> None:
        """FlateDecode does not trigger LPDF_IMG_004."""
        event = _make_image_event(filters=("FlateDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        comp_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_004"]
        assert len(comp_findings) == 0

    @staticmethod
    def test_inline_image_finding() -> None:
        """Inline image triggers LPDF_IMG_005."""
        event = _make_image_event(is_inline=True)
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        inline_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_005"]
        assert len(inline_findings) == 1

    @staticmethod
    def test_degenerate_ctm_no_dpi_findings() -> None:
        """Degenerate CTM skips DPI findings (invalid result)."""
        event = _make_image_event(
            ctm=TransformationMatrix(a=0, b=0, c=0, d=0, e=0, f=0),
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        dpi_findings = [f for f in findings if f.inspection_id in ("LPDF_IMG_001", "LPDF_IMG_002")]
        assert len(dpi_findings) == 0


class TestColorSpaceMismatch:
    """Test LPDF_IMG_003 color space mismatch check."""

    @staticmethod
    def test_rgb_in_cmyk_workflow() -> None:
        event = _make_image_event(color_space="DeviceRGB")
        analyzer = ImageAnalyzer()
        finding = analyzer.check_color_space_mismatch(event, "CMYK")
        assert finding is not None
        assert finding.inspection_id == "LPDF_IMG_003"

    @staticmethod
    def test_cmyk_in_cmyk_workflow_ok() -> None:
        event = _make_image_event(color_space="DeviceCMYK")
        analyzer = ImageAnalyzer()
        finding = analyzer.check_color_space_mismatch(event, "CMYK")
        assert finding is None

    @staticmethod
    def test_cmyk_in_rgb_workflow() -> None:
        event = _make_image_event(color_space="DeviceCMYK")
        analyzer = ImageAnalyzer()
        finding = analyzer.check_color_space_mismatch(event, "RGB")
        assert finding is not None
        assert finding.inspection_id == "LPDF_IMG_003"


class TestLZWCompression:
    """Test LPDF_IMG_007: LZW compression detection."""

    @staticmethod
    def test_lzw_triggers_delay() -> None:
        """LZWDecode filter triggers LPDF_IMG_007."""
        event = _make_image_event(filters=("LZWDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        lzw_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_007"]
        assert len(lzw_findings) == 1
        assert lzw_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_lzw_with_other_filters() -> None:
        """LZWDecode combined with other filters still triggers."""
        event = _make_image_event(filters=("LZWDecode", "ASCIIHexDecode"))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        lzw_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_007"]
        assert len(lzw_findings) == 1

    @staticmethod
    def test_flate_no_lzw_finding() -> None:
        """FlateDecode does not trigger LPDF_IMG_007."""
        event = _make_image_event(filters=("FlateDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        lzw_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_007"]
        assert len(lzw_findings) == 0

    @staticmethod
    def test_lzw_details_contain_filters() -> None:
        event = _make_image_event(filters=("LZWDecode",), image_name="Im5")
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        lzw = next((f for f in findings if f.inspection_id == "LPDF_IMG_007"), None)
        assert lzw is not None
        assert lzw.details["image_name"] == "Im5"
        assert "LZWDecode" in lzw.details["filters"]


class TestJPEG2000:
    """Test LPDF_IMG_008: JPEG2000 image detection."""

    @staticmethod
    def test_jpx_triggers_advisory() -> None:
        """JPXDecode filter triggers LPDF_IMG_008."""
        event = _make_image_event(filters=("JPXDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        jpx_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_008"]
        assert len(jpx_findings) == 1
        assert jpx_findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_dcte_no_jpx_finding() -> None:
        """DCTDecode (JPEG) does not trigger LPDF_IMG_008."""
        event = _make_image_event(filters=("DCTDecode",))
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        jpx_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_008"]
        assert len(jpx_findings) == 0

    @staticmethod
    def test_jpx_page_num_in_message() -> None:
        event = _make_image_event(filters=("JPXDecode",), page_num=3)
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        jpx = next((f for f in findings if f.inspection_id == "LPDF_IMG_008"), None)
        assert jpx is not None
        assert jpx.page_num == 3


class TestSixteenBitImage:
    """Test LPDF_IMG_009: 16-bit image detection."""

    @staticmethod
    def test_16bit_triggers_advisory() -> None:
        """bits_per_component=16 triggers LPDF_IMG_009."""
        event16 = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            bits_per_component=16,
            color_space="DeviceRGB",
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event16])
        bit_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_009"]
        assert len(bit_findings) == 1
        assert bit_findings[0].severity == Severity.ADVISORY
        assert bit_findings[0].details["bits_per_component"] == 16

    @staticmethod
    def test_8bit_no_finding() -> None:
        """bits_per_component=8 does not trigger LPDF_IMG_009."""
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            bits_per_component=8,
            color_space="DeviceRGB",
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        bit_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_009"]
        assert len(bit_findings) == 0

    @staticmethod
    def test_1bit_no_finding() -> None:
        """bits_per_component=1 (bitmap) does not trigger LPDF_IMG_009."""
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            bits_per_component=1,
            color_space="DeviceGray",
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        bit_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_009"]
        assert len(bit_findings) == 0


class TestOPIReference:
    """Test LPDF_IMG_010: OPI reference detection."""

    @staticmethod
    def test_opi_triggers_aground() -> None:
        """has_opi=True triggers LPDF_IMG_010."""
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            has_opi=True,
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        opi_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_010"]
        assert len(opi_findings) == 1
        assert opi_findings[0].severity == Severity.ERROR

    @staticmethod
    def test_no_opi_no_finding() -> None:
        """has_opi=False does not trigger LPDF_IMG_010."""
        event = _make_image_event()
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        opi_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_010"]
        assert len(opi_findings) == 0

    @staticmethod
    def test_opi_object_metadata() -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=2,
            operator_index=0,
            image_name="Im7",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            has_opi=True,
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        opi = next((f for f in findings if f.inspection_id == "LPDF_IMG_010"), None)
        assert opi is not None
        assert opi.object_id == "Im7"
        assert opi.object_type == "image"


class TestAlternateImages:
    """Test LPDF_IMG_011: Alternate images detection."""

    @staticmethod
    def test_alternate_triggers_delay() -> None:
        """has_alternate=True triggers LPDF_IMG_011."""
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            has_alternate=True,
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        alt_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_011"]
        assert len(alt_findings) == 1
        assert alt_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_no_alternate_no_finding() -> None:
        """has_alternate=False does not trigger LPDF_IMG_011."""
        event = _make_image_event()
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        alt_findings = [f for f in findings if f.inspection_id == "LPDF_IMG_011"]
        assert len(alt_findings) == 0

    @staticmethod
    def test_alternate_details() -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im3",
            ctm=TransformationMatrix(a=200, b=0, c=0, d=300, e=0, f=0),
            pixel_width=1000,
            pixel_height=800,
            has_alternate=True,
        )
        analyzer = ImageAnalyzer()
        findings = analyzer.analyze(_make_document(), [event])
        alt = next((f for f in findings if f.inspection_id == "LPDF_IMG_011"), None)
        assert alt is not None
        assert alt.details["image_name"] == "Im3"
