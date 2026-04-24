"""Minimal sfnt (TrueType / OpenType) parser for font-license inspection.

Extracts the OS/2 table's ``fsType`` field from an embedded font program so
``FontAnalyzer`` can detect fonts whose embedding licence may be
restricted. The parser is deliberately tiny — no fonttools dependency, no
glyph access, just enough structure to locate one uint16.

Spec refs:
  - ISO 32000-2 §9.8.2 (PDF font-descriptor stream formats)
  - Microsoft OpenType Specification, OS/2 table §1.2 (fsType field)
  - Apple TrueType Reference Manual, sfnt structure
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = ["FsTypeInfo", "format_fstype_flags", "parse_fstype"]


# fsType bits — Microsoft OpenType OS/2 §1.2 table.
_FSTYPE_FLAG_LABELS = {
    1: "restricted_license_embedding",
    2: "preview_and_print_embedding",
    3: "editable_embedding",
    8: "no_subsetting",
    9: "bitmap_only",
}

# Embedding-restriction bits (the ones that change severity vs pure info).
_EMBEDDING_RESTRICTION_BITS = {1, 2, 3}


@dataclass(frozen=True)
class FsTypeInfo:
    """Parsed fsType classification for a single font."""

    value: int
    """Raw fsType uint16."""

    flags: list[str]
    """Human-readable flag names that were set (e.g.
    ``["preview_and_print_embedding"]``)."""

    has_embedding_restriction: bool
    """True if any of bits 1, 2, or 3 is set — embedding the font in this
    PDF may violate the vendor's licence."""

    no_subsetting: bool
    """Bit 8 — font must be embedded whole; subsetting is forbidden."""

    bitmap_only: bool
    """Bit 9 — only bitmap data may be embedded (not outlines)."""


def parse_fstype(font_bytes: bytes) -> FsTypeInfo | None:
    """Parse fsType from an embedded sfnt font program.

    Accepts:
      - TrueType outlines (sfnt version 0x00010000)
      - OpenType/CFF outlines (sfnt version b"OTTO")
      - TrueType Collections are NOT supported here — callers embed a
        single face per PDF font, not a TTC wrapper.

    Returns ``None`` when the bytes don't parse as a recognised sfnt
    format, or when no OS/2 table is present (CFF fonts can omit it in
    rare cases). Never raises — any structural problem produces ``None``.
    """
    if not font_bytes or len(font_bytes) < 12:
        return None

    try:
        # sfnt header: uint32 version, uint16 numTables, uint16 searchRange,
        # uint16 entrySelector, uint16 rangeShift.
        sfnt_version = font_bytes[:4]
        if sfnt_version not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"):
            return None
        num_tables = struct.unpack(">H", font_bytes[4:6])[0]

        table_dir_start = 12
        table_record_size = 16
        table_dir_end = table_dir_start + num_tables * table_record_size
        if len(font_bytes) < table_dir_end:
            return None

        os2_offset: int | None = None
        os2_length: int | None = None
        for i in range(num_tables):
            rec = font_bytes[
                table_dir_start + i * table_record_size : table_dir_start
                + (i + 1) * table_record_size
            ]
            tag = rec[:4]
            # uint32 checksum, uint32 offset, uint32 length — checksum
            # isn't validated; a hostile artwork still parses fine.
            _, offset, length = struct.unpack(">III", rec[4:16])
            if tag == b"OS/2":
                os2_offset = offset
                os2_length = length
                break

        if os2_offset is None or os2_length is None:
            return None

        # OS/2 table layout (Microsoft spec):
        #   uint16 version, int16 xAvgCharWidth, uint16 usWeightClass,
        #   uint16 usWidthClass, uint16 fsType, ...
        # fsType sits at offset 8.
        if len(font_bytes) < os2_offset + 10:
            return None
        fs_type_value = struct.unpack(">H", font_bytes[os2_offset + 8 : os2_offset + 10])[0]
    except struct.error:
        return None

    flags = format_fstype_flags(fs_type_value)
    return FsTypeInfo(
        value=fs_type_value,
        flags=flags,
        has_embedding_restriction=any(
            fs_type_value & (1 << bit) for bit in _EMBEDDING_RESTRICTION_BITS
        ),
        no_subsetting=bool(fs_type_value & (1 << 8)),
        bitmap_only=bool(fs_type_value & (1 << 9)),
    )


def format_fstype_flags(value: int) -> list[str]:
    """Return the human-readable flag names set in ``value``.

    Empty list (value == 0) means "installable embedding" — the most
    permissive licence. Callers treat the empty list as a silent pass.
    """
    if value == 0:
        return []
    out: list[str] = []
    for bit, label in _FSTYPE_FLAG_LABELS.items():
        if value & (1 << bit):
            out.append(label)
    return out
