"""Tests for the upload security module."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from lintpdf.api.upload_security import (
    DANGEROUS_EXTENSIONS,
    PDF_TYPES,
    PRINT_READY_TYPES,
    sanitize_filename,
    validate_upload,
)

# ---------------------------------------------------------------------------
# Minimal valid file byte sequences for magic-bytes detection
# ---------------------------------------------------------------------------

# PNG: 8-byte signature + minimal IHDR chunk (enough for filetype lib)
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"  # PNG signature
    b"\x00\x00\x00\rIHDR"  # IHDR chunk header
    b"\x00\x00\x00\x01"  # width: 1
    b"\x00\x00\x00\x01"  # height: 1
    b"\x08\x02"  # bit depth: 8, color type: RGB
    b"\x00\x00\x00"  # compression, filter, interlace
    b"\x90wS\xde"  # CRC
    b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND chunk
)

# JPEG: minimal JFIF header
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0"  # SOI + APP0 marker
    b"\x00\x10JFIF\x00"  # JFIF identifier
    b"\x01\x01\x00\x00\x01\x00\x01\x00\x00"  # version, density
    b"\xff\xd9"  # EOI
)

# GIF89a minimal header
MINIMAL_GIF = (
    b"GIF89a"  # signature + version
    b"\x01\x00\x01\x00"  # 1x1 pixels
    b"\x00\x00\x00"  # GCT flag, background, aspect ratio
    b"\x00\x00\x00\x00\x00\x00"  # minimal color table
    b"\x3b"  # trailer
)

# WebP: RIFF container with VP8 header
MINIMAL_WEBP = (
    b"RIFF"
    b"\x24\x00\x00\x00"  # file size
    b"WEBP"
    b"VP8 "
    b"\x18\x00\x00\x00"  # chunk size
    b"\x30\x01\x00\x9d\x01\x2a"  # VP8 bitstream header
    b"\x01\x00\x01\x00"  # width, height
    b"\x01\x40\x25\xa4\x00\x03"
    b"\x70\x00\xfe\xfb\x94\x00\x00"
)

# TIFF: little-endian minimal header
MINIMAL_TIFF = (
    b"II"  # little-endian byte order
    b"\x2a\x00"  # TIFF magic number
    b"\x08\x00\x00\x00"  # offset to first IFD
    b"\x00\x00"  # zero entries (minimal)
)

# PSD: Photoshop signature
MINIMAL_PSD = (
    b"8BPS"  # signature
    b"\x00\x01"  # version
    b"\x00\x00\x00\x00\x00\x00"  # reserved
    b"\x00\x03"  # channels
    b"\x00\x00\x00\x01"  # height
    b"\x00\x00\x00\x01"  # width
    b"\x00\x08"  # depth
    b"\x00\x03"  # color mode (RGB)
)

# PDF: minimal header
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"xref\n0 3\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
    b"startxref\n115\n%%EOF\n"
)

# EPS: ASCII header
MINIMAL_EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\n%%EOF\n"

# EPS: binary header
MINIMAL_EPS_BINARY = b"\xc5\xd0\xd3\xc6" + b"\x00" * 26

# InDesign: magic bytes
MINIMAL_INDD = b"\x06\x06\xed\xf5\xd8\x1d\x46\xe5" + b"\x00" * 100

# SVG: safe minimal
MINIMAL_SVG = (
    b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'
)

# SVG: with script (unsafe)
SVG_WITH_SCRIPT = (
    b'<?xml version="1.0"?>\n'
    b'<svg xmlns="http://www.w3.org/2000/svg">'
    b"<script>alert('xss')</script></svg>"
)

# SVG: with event handler (unsafe)
SVG_WITH_EVENT = (
    b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
)

# SVG: with javascript: URI (unsafe)
SVG_WITH_JS_URI = (
    b'<?xml version="1.0"?>\n'
    b'<svg xmlns="http://www.w3.org/2000/svg">'
    b'<a href="javascript:alert(1)"><text>click</text></a></svg>'
)

# SVG: with foreignObject (unsafe)
SVG_WITH_FOREIGN = (
    b'<?xml version="1.0"?>\n'
    b'<svg xmlns="http://www.w3.org/2000/svg">'
    b"<foreignObject><body>html</body></foreignObject></svg>"
)


def _make_upload(content: bytes, filename: str) -> UploadFile:
    """Create a mock UploadFile with the given content and filename."""
    return UploadFile(file=io.BytesIO(content), filename=filename)


# ---------------------------------------------------------------------------
# sanitize_filename tests
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_basic_filename(self) -> None:
        assert sanitize_filename("test.pdf") == "test.pdf"

    def test_strips_unix_path_components(self) -> None:
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("/var/tmp/evil.pdf") == "evil.pdf"

    def test_strips_windows_path_components(self) -> None:
        assert sanitize_filename("C:\\Windows\\evil.exe") == "evil.exe"

    def test_removes_null_bytes(self) -> None:
        assert sanitize_filename("test\x00.pdf") == "test.pdf"

    def test_removes_control_characters(self) -> None:
        assert sanitize_filename("test\x01\x02.pdf") == "test.pdf"

    def test_none_filename_raises(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename(None)
        assert exc_info.value.status_code == 422

    def test_empty_filename_raises(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("")
        assert exc_info.value.status_code == 422

    def test_only_control_chars_raises(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("\x00\x01\x02")
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# validate_upload tests — PDF types
# ---------------------------------------------------------------------------


class TestValidateUploadPDF:
    @pytest.mark.asyncio
    async def test_valid_pdf(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "document.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES)
        assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_valid_pdf_uppercase_extension(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "DOCUMENT.PDF")
        content = await validate_upload(upload, allowed_types=PDF_TYPES)
        assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_pdf_wrong_extension(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "document.txt")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422
        assert "not allowed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_pdf_fake_content(self) -> None:
        """A .pdf extension with JPEG content should be rejected."""
        upload = _make_upload(MINIMAL_JPEG, "fake.pdf")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_file(self) -> None:
        upload = _make_upload(b"", "empty.pdf")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422
        assert "empty" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_no_filename(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# validate_upload tests — image types
# ---------------------------------------------------------------------------


class TestValidateUploadImages:
    @pytest.mark.asyncio
    async def test_valid_png(self) -> None:
        upload = _make_upload(MINIMAL_PNG, "logo.png")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_PNG

    @pytest.mark.asyncio
    async def test_valid_jpeg_jpg(self) -> None:
        upload = _make_upload(MINIMAL_JPEG, "photo.jpg")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_JPEG

    @pytest.mark.asyncio
    async def test_valid_jpeg_jpeg(self) -> None:
        upload = _make_upload(MINIMAL_JPEG, "photo.jpeg")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_JPEG

    @pytest.mark.asyncio
    async def test_valid_gif(self) -> None:
        upload = _make_upload(MINIMAL_GIF, "anim.gif")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_GIF

    @pytest.mark.asyncio
    async def test_valid_tiff(self) -> None:
        upload = _make_upload(MINIMAL_TIFF, "scan.tif")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_TIFF

    @pytest.mark.asyncio
    async def test_valid_tiff_ext(self) -> None:
        upload = _make_upload(MINIMAL_TIFF, "scan.tiff")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_TIFF

    @pytest.mark.asyncio
    async def test_valid_psd(self) -> None:
        upload = _make_upload(MINIMAL_PSD, "design.psd")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_PSD

    @pytest.mark.asyncio
    async def test_mime_mismatch_png_ext_jpeg_content(self) -> None:
        """A .png extension on JPEG content should be rejected."""
        upload = _make_upload(MINIMAL_JPEG, "fake.png")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "does not match extension" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_exe_rejected(self) -> None:
        """An .exe file should be rejected even with valid-looking content."""
        upload = _make_upload(b"MZ" + b"\x00" * 100, "malware.exe")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "not allowed" in exc_info.value.detail


# ---------------------------------------------------------------------------
# validate_upload tests — custom detection (EPS, InDesign)
# ---------------------------------------------------------------------------


class TestValidateUploadCustomFormats:
    @pytest.mark.asyncio
    async def test_valid_eps_ascii(self) -> None:
        upload = _make_upload(MINIMAL_EPS, "artwork.eps")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_EPS

    @pytest.mark.asyncio
    async def test_valid_eps_binary(self) -> None:
        upload = _make_upload(MINIMAL_EPS_BINARY, "artwork.eps")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_EPS_BINARY

    @pytest.mark.asyncio
    async def test_valid_indd(self) -> None:
        upload = _make_upload(MINIMAL_INDD, "layout.indd")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_INDD

    @pytest.mark.asyncio
    async def test_eps_wrong_content(self) -> None:
        """An .eps extension with random content should be rejected."""
        upload = _make_upload(b"not postscript content at all", "fake.eps")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_indd_wrong_content(self) -> None:
        """An .indd extension with wrong magic should be rejected."""
        upload = _make_upload(b"\x00" * 100, "fake.indd")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# validate_upload tests — SVG safety
# ---------------------------------------------------------------------------


class TestValidateUploadSVG:
    @pytest.mark.asyncio
    async def test_valid_svg(self) -> None:
        upload = _make_upload(MINIMAL_SVG, "icon.svg")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == MINIMAL_SVG

    @pytest.mark.asyncio
    async def test_svg_with_script_rejected(self) -> None:
        upload = _make_upload(SVG_WITH_SCRIPT, "evil.svg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "script" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_svg_with_event_handler_rejected(self) -> None:
        upload = _make_upload(SVG_WITH_EVENT, "evil.svg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "event handler" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_svg_with_javascript_uri_rejected(self) -> None:
        upload = _make_upload(SVG_WITH_JS_URI, "evil.svg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "uri" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_svg_with_foreign_object_rejected(self) -> None:
        upload = _make_upload(SVG_WITH_FOREIGN, "evil.svg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "foreignobject" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_svg_not_in_pdf_types(self) -> None:
        """SVG should be rejected when only PDF_TYPES is allowed."""
        upload = _make_upload(MINIMAL_SVG, "icon.svg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# validate_upload tests — QuarkXPress (extension-only)
# ---------------------------------------------------------------------------


class TestValidateUploadQuark:
    @pytest.mark.asyncio
    async def test_valid_qxp(self) -> None:
        """QuarkXPress files pass with extension-only validation."""
        upload = _make_upload(b"\x00" * 100, "layout.qxp")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == b"\x00" * 100

    @pytest.mark.asyncio
    async def test_valid_qxd(self) -> None:
        upload = _make_upload(b"\x00" * 100, "layout.qxd")
        content = await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert content == b"\x00" * 100


# ---------------------------------------------------------------------------
# validate_upload tests — double extension attacks
# ---------------------------------------------------------------------------


class TestDoubleExtensionAttack:
    @pytest.mark.asyncio
    async def test_php_png_rejected(self) -> None:
        upload = _make_upload(MINIMAL_PNG, "malware.php.png")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "suspicious" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_exe_jpg_rejected(self) -> None:
        upload = _make_upload(MINIMAL_JPEG, "trojan.exe.jpg")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PRINT_READY_TYPES)
        assert exc_info.value.status_code == 422
        assert "suspicious" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_html_pdf_rejected(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "phishing.html.pdf")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_safe_double_dot_allowed(self) -> None:
        """A filename like 'my.document.pdf' should be fine (no dangerous interior ext)."""
        upload = _make_upload(MINIMAL_PDF, "my.document.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES)
        assert content == MINIMAL_PDF


# ---------------------------------------------------------------------------
# validate_upload tests — path traversal filenames
# ---------------------------------------------------------------------------


class TestPathTraversal:
    @pytest.mark.asyncio
    async def test_path_traversal_stripped(self) -> None:
        """Path components are stripped, then extension is validated."""
        upload = _make_upload(MINIMAL_PDF, "../../etc/passwd")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES)
        # "passwd" has no .pdf extension
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_path_traversal_with_valid_ext(self) -> None:
        """Path traversal with valid extension — path stripped, file accepted."""
        upload = _make_upload(MINIMAL_PDF, "../../uploads/doc.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES)
        assert content == MINIMAL_PDF


# ---------------------------------------------------------------------------
# validate_upload tests — size limits
# ---------------------------------------------------------------------------


class TestSizeLimits:
    @pytest.mark.asyncio
    async def test_size_exceeded(self) -> None:
        big_content = MINIMAL_PDF + b"\x00" * 1000
        upload = _make_upload(big_content, "big.pdf")
        with pytest.raises(HTTPException) as exc_info:
            await validate_upload(upload, allowed_types=PDF_TYPES, max_size_bytes=100)
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_size_within_limit(self) -> None:
        upload = _make_upload(MINIMAL_PDF, "ok.pdf")
        content = await validate_upload(
            upload, allowed_types=PDF_TYPES, max_size_bytes=len(MINIMAL_PDF) + 1
        )
        assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_size_none_skips_check(self) -> None:
        big_content = MINIMAL_PDF + b"\x00" * 10000
        upload = _make_upload(big_content, "big.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES, max_size_bytes=None)
        assert content == big_content


# ---------------------------------------------------------------------------
# ClamAV scanning tests
# ---------------------------------------------------------------------------


class TestClamAVScanning:
    @pytest.mark.asyncio
    async def test_scan_skipped_when_no_url(self) -> None:
        """When settings.clamav_url is unset, scanning is skipped (fail-open).

        The production railway-clamav sidecar is unreliable, so scan failures
        must not block uploads. Only positive malware detection raises 422.
        """
        settings = MagicMock()
        settings.clamav_url = None
        upload = _make_upload(MINIMAL_PDF, "clean.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES, settings=settings)
        assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_scan_rejects_malware(self) -> None:
        """When ClamAV detects malware, the upload is rejected."""
        settings = MagicMock()
        settings.clamav_url = "localhost:3310"

        mock_scanner = MagicMock()
        mock_scanner.instream.return_value = {"stream": ("FOUND", "Eicar-Test-Signature")}

        with patch("lintpdf.api.upload_security._clamd_mod") as mock_clamd:
            mock_clamd.ClamdNetworkSocket.return_value = mock_scanner
            upload = _make_upload(MINIMAL_PDF, "infected.pdf")
            with pytest.raises(HTTPException) as exc_info:
                await validate_upload(upload, allowed_types=PDF_TYPES, settings=settings)
            assert exc_info.value.status_code == 422
            assert "malware" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_scan_allows_clean_file(self) -> None:
        """When ClamAV says OK, the upload proceeds."""
        settings = MagicMock()
        settings.clamav_url = "localhost:3310"

        mock_scanner = MagicMock()
        mock_scanner.instream.return_value = {"stream": ("OK", None)}

        with patch("lintpdf.api.upload_security._clamd_mod") as mock_clamd:
            mock_clamd.ClamdNetworkSocket.return_value = mock_scanner
            upload = _make_upload(MINIMAL_PDF, "clean.pdf")
            content = await validate_upload(upload, allowed_types=PDF_TYPES, settings=settings)
            assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_scan_fails_open_on_unreachable(self) -> None:
        """When ClamAV is unreachable, the upload proceeds (fail-open).

        Connection errors against clamd must not block uploads because the
        sidecar is unreliable. Positive malware detection still raises 422.
        """
        settings = MagicMock()
        settings.clamav_url = "unreachable:3310"

        with patch("lintpdf.api.upload_security._clamd_mod") as mock_clamd:
            mock_clamd.ClamdNetworkSocket.side_effect = ConnectionError("unreachable")
            upload = _make_upload(MINIMAL_PDF, "file.pdf")
            content = await validate_upload(upload, allowed_types=PDF_TYPES, settings=settings)
            assert content == MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_scan_skipped_when_no_settings(self) -> None:
        """When no settings object is passed, scanning is entirely skipped.

        This is the internal/test-only path — production callers always pass settings.
        """
        upload = _make_upload(MINIMAL_PDF, "clean.pdf")
        content = await validate_upload(upload, allowed_types=PDF_TYPES, settings=None)
        assert content == MINIMAL_PDF


# ---------------------------------------------------------------------------
# Registry completeness checks
# ---------------------------------------------------------------------------


class TestTypeRegistries:
    def test_pdf_types_only_pdf(self) -> None:
        assert len(PDF_TYPES) == 1
        pdf_type = next(iter(PDF_TYPES))
        assert pdf_type.mime_type == "application/pdf"

    def test_print_ready_covers_all_formats(self) -> None:
        mimes = {t.mime_type for t in PRINT_READY_TYPES}
        expected = {
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/webp",
            "image/gif",
            "application/pdf",
            "image/vnd.adobe.photoshop",
            "application/postscript",
            "application/x-indesign",
            "image/svg+xml",
            "application/x-quark-xpress",
            "application/vnd.cip4-jdf+xml",
            "application/vnd.cip4-xjdf+xml",
        }
        assert mimes == expected

    def test_dangerous_extensions_exist(self) -> None:
        assert ".php" in DANGEROUS_EXTENSIONS
        assert ".exe" in DANGEROUS_EXTENSIONS
        assert ".js" in DANGEROUS_EXTENSIONS
        assert ".html" in DANGEROUS_EXTENSIONS
