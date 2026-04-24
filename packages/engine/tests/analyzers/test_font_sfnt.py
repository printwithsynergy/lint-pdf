"""Tests for the minimal sfnt parser + LPDF_FONT_015 fsType check."""

from __future__ import annotations

import struct

from lintpdf.analyzers._font_sfnt import (
    FsTypeInfo,
    format_fstype_flags,
    parse_fstype,
)
from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.font import FontAnalyzer
from lintpdf.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage

# ---------------------------------------------------------------------------
# Helpers — hand-craft a minimal sfnt with a single OS/2 table.
# ---------------------------------------------------------------------------


def _build_minimal_sfnt(fs_type: int) -> bytes:
    """Return a valid-enough sfnt byte blob with one OS/2 table.

    Layout:
      - sfnt header (12 bytes): TrueType version 0x00010000, numTables=1.
      - table directory record (16 bytes): tag=OS/2, checksum=0,
        offset=28, length=96 (covers through fsType + padding).
      - OS/2 table body (96 bytes): fields we don't care about zeroed
        except fsType at offset 8.
    """
    sfnt_header = struct.pack(
        ">IHHHH",
        0x00010000,  # version
        1,  # numTables
        16,  # searchRange — unused by our parser
        0,  # entrySelector
        0,  # rangeShift
    )
    os2_body_len = 96
    os2_offset = 12 + 16  # sfnt header + one table record
    table_record = struct.pack(
        ">4sIII",
        b"OS/2",  # tag
        0,  # checksum
        os2_offset,
        os2_body_len,
    )
    # OS/2 body: 2 bytes version + 2 bytes xAvgCharWidth + 2 usWeightClass
    # + 2 usWidthClass + 2 fsType + 86 bytes padding.
    os2_body = (
        struct.pack(">H", 4)  # version 4
        + struct.pack(">h", 0)  # xAvgCharWidth
        + struct.pack(">H", 400)  # usWeightClass (regular)
        + struct.pack(">H", 5)  # usWidthClass (normal)
        + struct.pack(">H", fs_type)  # fsType — the field under test
        + b"\x00" * (os2_body_len - 10)
    )
    return sfnt_header + table_record + os2_body


# ---------------------------------------------------------------------------
# parse_fstype
# ---------------------------------------------------------------------------


class TestParseFstype:
    @staticmethod
    def test_installable_returns_zero() -> None:
        info = parse_fstype(_build_minimal_sfnt(fs_type=0))
        assert isinstance(info, FsTypeInfo)
        assert info.value == 0
        assert info.flags == []
        assert info.has_embedding_restriction is False
        assert info.no_subsetting is False
        assert info.bitmap_only is False

    @staticmethod
    def test_preview_and_print_flagged() -> None:
        # Bit 2 — preview & print only.
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0004))
        assert info is not None
        assert info.value == 0x0004
        assert info.flags == ["preview_and_print_embedding"]
        assert info.has_embedding_restriction is True
        assert info.no_subsetting is False

    @staticmethod
    def test_restricted_flagged() -> None:
        # Bit 1 — restricted licence.
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0002))
        assert info is not None
        assert info.flags == ["restricted_license_embedding"]
        assert info.has_embedding_restriction is True

    @staticmethod
    def test_editable_flagged() -> None:
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0008))
        assert info is not None
        assert info.flags == ["editable_embedding"]
        assert info.has_embedding_restriction is True

    @staticmethod
    def test_no_subsetting_reported_without_restriction() -> None:
        # Bit 8 only — no embedding restriction, but subsetting forbidden.
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0100))
        assert info is not None
        assert info.value == 0x0100
        assert info.no_subsetting is True
        assert info.has_embedding_restriction is False
        assert info.flags == ["no_subsetting"]

    @staticmethod
    def test_bitmap_only_reported() -> None:
        # Bit 9 — bitmap only.
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0200))
        assert info is not None
        assert info.bitmap_only is True
        assert info.flags == ["bitmap_only"]

    @staticmethod
    def test_combined_bits() -> None:
        # Preview & print + no subsetting.
        info = parse_fstype(_build_minimal_sfnt(fs_type=0x0104))
        assert info is not None
        assert "preview_and_print_embedding" in info.flags
        assert "no_subsetting" in info.flags
        assert info.has_embedding_restriction is True
        assert info.no_subsetting is True

    @staticmethod
    def test_otto_sfnt_accepted() -> None:
        """OpenType/CFF fonts use b'OTTO' as the sfnt version tag."""
        # Rebuild with OTTO header.
        body = _build_minimal_sfnt(fs_type=0x0004)
        otto = b"OTTO" + body[4:]
        info = parse_fstype(otto)
        assert info is not None
        assert info.value == 0x0004

    @staticmethod
    def test_garbage_bytes_returns_none() -> None:
        assert parse_fstype(b"") is None
        assert parse_fstype(b"not-a-font") is None
        assert parse_fstype(b"\xde\xad\xbe\xef" + b"\x00" * 200) is None

    @staticmethod
    def test_truncated_table_returns_none() -> None:
        """sfnt header claims more tables than the buffer actually holds."""
        truncated = struct.pack(">IHHHH", 0x00010000, 10, 128, 3, 32)
        assert parse_fstype(truncated) is None

    @staticmethod
    def test_missing_os2_returns_none() -> None:
        """Valid sfnt with only a head table (no OS/2) → None."""
        sfnt_header = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
        table_record = struct.pack(">4sIII", b"head", 0, 28, 54)
        body = b"\x00" * 54
        assert parse_fstype(sfnt_header + table_record + body) is None


class TestFormatFstypeFlags:
    @staticmethod
    def test_empty_for_zero() -> None:
        assert format_fstype_flags(0) == []

    @staticmethod
    def test_orders_by_bit_position() -> None:
        flags = format_fstype_flags(0x030E)  # bits 1, 2, 3, 8, 9
        assert flags == [
            "restricted_license_embedding",
            "preview_and_print_embedding",
            "editable_embedding",
            "no_subsetting",
            "bitmap_only",
        ]


# ---------------------------------------------------------------------------
# FontAnalyzer._check_fstype integration
# ---------------------------------------------------------------------------


def _make_font(
    *,
    embedded: bool = True,
    font_type: str = "TrueType",
    base_font: str = "ABCDEF+Helvetica",
) -> PdfFont:
    return PdfFont(
        name="F1",
        base_font=base_font,
        font_type=font_type,
        embedded=embedded,
        subset=True,
        font_descriptor={"/FontFile2": {"/Length": 1000}},
    )


class TestCheckFstypeBranch:
    @staticmethod
    def test_restricted_font_fires() -> None:
        font = _make_font()
        bytes_ = _build_minimal_sfnt(fs_type=0x0004)
        findings = FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=bytes_)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_FONT_015"
        assert f.severity == Severity.ADVISORY
        assert f.details["fs_type_value"] == 0x0004
        assert f.details["fs_type_flags"] == ["preview_and_print_embedding"]

    @staticmethod
    def test_installable_font_silent() -> None:
        font = _make_font()
        bytes_ = _build_minimal_sfnt(fs_type=0x0000)
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=bytes_) == []

    @staticmethod
    def test_no_subsetting_bit_alone_is_silent() -> None:
        """no_subsetting on its own is info-only — no finding emitted."""
        font = _make_font()
        bytes_ = _build_minimal_sfnt(fs_type=0x0100)
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=bytes_) == []

    @staticmethod
    def test_type1_font_skipped() -> None:
        """Type 1 fonts have no OS/2 table; skip even if bytes were passed."""
        font = _make_font(font_type="Type1")
        bytes_ = _build_minimal_sfnt(fs_type=0x0004)
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=bytes_) == []

    @staticmethod
    def test_type3_font_skipped() -> None:
        """Type 3 fonts (user-drawn glyphs) — skip."""
        font = _make_font(font_type="Type3")
        bytes_ = _build_minimal_sfnt(fs_type=0x0004)
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=bytes_) == []

    @staticmethod
    def test_missing_bytes_skipped() -> None:
        """No bytes passed → silent no-op (pdf_bytes wasn't provided to analyzer)."""
        font = _make_font()
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=None) == []

    @staticmethod
    def test_unparseable_bytes_skipped() -> None:
        """Corrupt font bytes → parser returns None → no finding."""
        font = _make_font()
        assert FontAnalyzer._check_fstype(font, page_num=1, font_file_bytes=b"garbage") == []


class TestAnalyzeIntegration:
    @staticmethod
    def test_analyze_without_pdf_bytes_skips_fstype() -> None:
        """FontAnalyzer() with no pdf_bytes → LPDF_FONT_015 never fires, even
        if other checks do."""
        doc = SemanticDocument(
            version="2.0",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    fonts={"F1": _make_font()},
                )
            ],
        )
        findings = FontAnalyzer().analyze(doc, events=[])
        assert all(f.inspection_id != "LPDF_FONT_015" for f in findings)
