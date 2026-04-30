"""Tests for BarcodeDecode AI analyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lintpdf.analyzers.finding import Severity


def _ctx(document, events=None, pdf_bytes=b"", ai_config=None):
    """Build an AnalyzerContext for analyze_v2 calls."""
    from lintpdf.plugin.protocol import AnalyzerContext

    return AnalyzerContext(
        document=document,
        events=events or [],
        pdf_bytes=pdf_bytes,
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


class TestBarcodeDecode:
    """Tests for BarcodeDecode analyzer with mocked image rendering and pyzbar."""

    @staticmethod
    def test_returns_empty_when_pyzbar_unavailable(minimal_semantic_doc: MagicMock) -> None:
        with patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", False):
            from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, pdf_bytes=b"fake_pdf"))

        assert findings == []

    @staticmethod
    def test_returns_empty_when_pil_unavailable(minimal_semantic_doc: MagicMock) -> None:
        with patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PIL", False):
            from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, pdf_bytes=b"fake_pdf"))

        assert findings == []

    @staticmethod
    def test_decodes_barcode_from_rendered_page(minimal_semantic_doc: MagicMock) -> None:
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
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_DMTX", False),
            patch(
                "lintpdf.ai.rendering.render_all_pages",
                return_value=[fake_png],
            ),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._pyzbar") as mock_pyzbar,
            patch("lintpdf.ai.analyzers.barcode.barcode_decode.PILImage") as mock_pil,
        ):
            mock_pyzbar.decode.return_value = [mock_item]
            mock_pil.open.return_value = MagicMock()

            from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, pdf_bytes=b"fake_pdf"))

        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_BC_001"
        assert f.severity == Severity.ADVISORY
        assert f.source == "ai"
        assert f.category == "barcode"
        assert "EAN-13" in f.message
        assert "5901234123457" in f.message
        assert f.details["symbology"] == "EAN-13"
        assert f.details["decoded_data"] == "5901234123457"

    @staticmethod
    def test_no_barcodes_produces_advisory(minimal_semantic_doc: MagicMock) -> None:
        fake_png = b"\x89PNG_fake"

        with (
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_DMTX", False),
            patch(
                "lintpdf.ai.rendering.render_all_pages",
                return_value=[fake_png],
            ),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._pyzbar") as mock_pyzbar,
            patch("lintpdf.ai.analyzers.barcode.barcode_decode.PILImage") as mock_pil,
        ):
            mock_pyzbar.decode.return_value = []
            mock_pil.open.return_value = MagicMock()

            from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, pdf_bytes=b"fake_pdf"))

        assert len(findings) == 1
        assert "No barcodes detected" in findings[0].message

    @staticmethod
    def test_rendering_failure_returns_empty(minimal_semantic_doc: MagicMock) -> None:
        with (
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PYZBAR", True),
            patch("lintpdf.ai.analyzers.barcode.barcode_decode._HAS_PIL", True),
            patch(
                "lintpdf.ai.rendering.render_all_pages",
                side_effect=RuntimeError("No rendering backend"),
            ),
        ):
            from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

            analyzer = BarcodeDecode()
            findings = analyzer.analyze_v2(_ctx(minimal_semantic_doc, pdf_bytes=b"fake_pdf"))

        assert findings == []

    @staticmethod
    def test_analyzer_metadata() -> None:
        from lintpdf.ai.analyzers.barcode.barcode_decode import BarcodeDecode

        analyzer = BarcodeDecode()
        assert analyzer.category == "barcode"
        assert analyzer.feature_slug == "barcode_decode"
        assert analyzer.tier == "cpu"
        assert analyzer.credits_per_run == 1
