"""Tests for BarcodeDecode AI analyzer."""

from __future__ import annotations

# skipcq: PYL-R0201
from unittest.mock import MagicMock, patch

from grounded.analyzers.finding import Severity


class TestBarcodeDecode:
    """Tests for BarcodeDecode analyzer with mocked image rendering and pyzbar."""

    def test_returns_empty_when_pyzbar_unavailable(self, minimal_semantic_doc: MagicMock) -> None:
        with patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", False):
            from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_returns_empty_when_pil_unavailable(self, minimal_semantic_doc: MagicMock) -> None:
        with patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PIL", False):
            from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_decodes_barcode_from_rendered_page(self, minimal_semantic_doc: MagicMock) -> None:
        # Mock pyzbar decoded item
        mock_item = MagicMock()
        mock_item.type = "EAN13"
        mock_item.data = b"5901234123457"
        mock_item.rect = MagicMock(left=100, top=200, width=150, height=50)

        # Create a fake PNG image (1x1 white pixel)
        fake_png = (
            b"\x89PNG\r\n\x1a\n"  # PNG signature
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0c"
            b"IDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with (
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_DMTX", False),
            patch(
                "grounded.ai.rendering.render_all_pages",
                return_value=[fake_png],
            ),
            patch("grounded.ai.analyzers.barcode.barcode_decode._pyzbar") as mock_pyzbar,
            patch("grounded.ai.analyzers.barcode.barcode_decode.PILImage") as mock_pil,
        ):
            mock_pyzbar.decode.return_value = [mock_item]
            mock_pil.open.return_value = MagicMock()

            from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "GRD_BC_001"
        assert f.severity == Severity.ADVISORY
        assert f.source == "ai"
        assert f.category == "barcode"
        assert "EAN-13" in f.message
        assert "5901234123457" in f.message
        assert f.details["symbology"] == "EAN-13"
        assert f.details["decoded_data"] == "5901234123457"

    def test_no_barcodes_produces_advisory(self, minimal_semantic_doc: MagicMock) -> None:
        fake_png = b"\x89PNG_fake"

        with (
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_DMTX", False),
            patch(
                "grounded.ai.rendering.render_all_pages",
                return_value=[fake_png],
            ),
            patch("grounded.ai.analyzers.barcode.barcode_decode._pyzbar") as mock_pyzbar,
            patch("grounded.ai.analyzers.barcode.barcode_decode.PILImage") as mock_pil,
        ):
            mock_pyzbar.decode.return_value = []
            mock_pil.open.return_value = MagicMock()

            from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert len(findings) == 1
        assert "No barcodes detected" in findings[0].message

    def test_rendering_failure_returns_empty(self, minimal_semantic_doc: MagicMock) -> None:
        with (
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("grounded.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch(
                "grounded.ai.rendering.render_all_pages",
                side_effect=RuntimeError("No rendering backend"),
            ),
        ):
            from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze(minimal_semantic_doc, [], b"fake_pdf")

        assert findings == []

    def test_analyzer_metadata(self) -> None:
        from grounded.ai.analyzers.barcode.barcode_decode import BarcodeDecode

        analyzer = BarcodeDecode()
        assert analyzer.category == "barcode"
        assert analyzer.feature_slug == "barcode_decode"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1
