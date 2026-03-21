"""Tests for IccProfileAnalyzer."""

import struct

from grounded.analyzers.icc_profile_analyzer import IccProfileAnalyzer
from grounded.analyzers.finding import Severity
from grounded.profiles.icc.profile_manager import (
    extract_icc_tags,
    validate_icc_profile_bytes,
)
from grounded.semantic.model import (
    SemanticDocument,
    SemanticPage,
    PdfBox,
    PdfColorSpace,
)


def _make_doc(output_intents=None, color_spaces=None):
    """Build a minimal SemanticDocument for testing."""
    page_cs = color_spaces or {}
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=page_cs,
    )
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        output_intents=output_intents or [],
        pages=[page],
    )


class TestIccProfileAnalyzer:
    def test_no_findings_on_clean_document(self):
        doc = _make_doc()
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        # No ICCBased spaces, no output intents = no ICC findings
        icc_findings = [f for f in findings if f.inspection_id.startswith("GRD_ICC_")]
        assert len(icc_findings) == 0

    def test_valid_icc_based_color_space(self):
        cs = PdfColorSpace(
            name="CS1", cs_type="ICCBased", components=4, icc_profile_ref="profile_1"
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        # Should have ICC_002 advisory for detected profile
        icc_002 = [f for f in findings if f.inspection_id == "GRD_ICC_002"]
        assert len(icc_002) >= 1

    def test_invalid_icc_component_count(self):
        cs = PdfColorSpace(
            name="CS1", cs_type="ICCBased", components=5, icc_profile_ref="profile_1"
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_001 = [f for f in findings if f.inspection_id == "GRD_ICC_001"]
        assert len(icc_001) >= 1
        assert icc_001[0].severity == Severity.AGROUND

    def test_missing_icc_profile_ref(self):
        cs = PdfColorSpace(name="CS1", cs_type="ICCBased", components=3, icc_profile_ref=None)
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_003 = [f for f in findings if f.inspection_id == "GRD_ICC_003"]
        assert len(icc_003) >= 1
        assert icc_003[0].severity == Severity.AGROUND

    def test_output_intent_validation(self):
        doc = _make_doc(output_intents=[{"S": "GTS_PDFX", "OutputConditionIdentifier": "FOGRA39"}])
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_005 = [f for f in findings if f.inspection_id == "GRD_ICC_005"]
        assert len(icc_005) >= 1

    def test_invalid_output_intent(self):
        doc = _make_doc(output_intents=[{"S": "INVALID_TYPE"}])
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_004 = [f for f in findings if f.inspection_id == "GRD_ICC_004"]
        assert len(icc_004) >= 1
        assert icc_004[0].severity == Severity.SQUALL

    def test_multiple_inconsistent_output_intents(self):
        doc = _make_doc(
            output_intents=[
                {"S": "GTS_PDFX", "OutputConditionIdentifier": "FOGRA39"},
                {"S": "GTS_PDFA1", "OutputConditionIdentifier": "sRGB"},
            ]
        )
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_006 = [f for f in findings if f.inspection_id == "GRD_ICC_006"]
        assert len(icc_006) >= 1


def _build_minimal_icc(
    *,
    profile_class: bytes = b"mntr",
    color_space: bytes = b"RGB ",
    pcs: bytes = b"XYZ ",
    version_major: int = 4,
    version_minor: int = 0,
    rendering_intent: int = 0,
    d50_x: float = 0.9642,
    d50_y: float = 1.0,
    d50_z: float = 0.8249,
    tags: dict[bytes, bytes] | None = None,
) -> bytes:
    """Build a minimal valid ICC profile binary for testing.

    Creates a header + tag directory + tag data structure.
    """
    if tags is None:
        # Minimal required tags for display profile
        tags = {
            b"desc": b"desc" + b"\x00" * 4 + struct.pack(">I", 5) + b"Test\x00",
            b"wtpt": b"XYZ "
            + b"\x00" * 4
            + struct.pack(">iii", int(0.9642 * 65536), int(1.0 * 65536), int(0.8249 * 65536)),
            b"cprt": b"text" + b"\x00" * 4 + b"(c) Test\x00",
            b"rXYZ": b"XYZ "
            + b"\x00" * 4
            + struct.pack(">iii", int(0.4361 * 65536), int(0.2225 * 65536), int(0.0139 * 65536)),
            b"gXYZ": b"XYZ "
            + b"\x00" * 4
            + struct.pack(">iii", int(0.3851 * 65536), int(0.7169 * 65536), int(0.0971 * 65536)),
            b"bXYZ": b"XYZ "
            + b"\x00" * 4
            + struct.pack(">iii", int(0.1431 * 65536), int(0.0606 * 65536), int(0.7141 * 65536)),
            b"rTRC": b"curv"
            + b"\x00" * 4
            + struct.pack(">I", 1)
            + struct.pack(">H", int(2.2 * 256)),
            b"gTRC": b"curv"
            + b"\x00" * 4
            + struct.pack(">I", 1)
            + struct.pack(">H", int(2.2 * 256)),
            b"bTRC": b"curv"
            + b"\x00" * 4
            + struct.pack(">I", 1)
            + struct.pack(">H", int(2.2 * 256)),
        }

    # Build header (128 bytes)
    header = bytearray(128)
    # Size (will be filled in at the end)
    # Version
    header[8] = version_major
    header[9] = version_minor << 4
    # Profile class
    header[12:16] = profile_class
    # Color space
    header[16:20] = color_space
    # PCS
    header[20:24] = pcs
    # Magic number
    header[36:40] = b"acsp"
    # Rendering intent
    header[67] = rendering_intent & 0x03
    # PCS illuminant D50
    struct.pack_into(">i", header, 68, int(d50_x * 65536))
    struct.pack_into(">i", header, 72, int(d50_y * 65536))
    struct.pack_into(">i", header, 76, int(d50_z * 65536))

    # Build tag directory
    tag_count = len(tags)
    tag_dir = struct.pack(">I", tag_count)

    # Calculate data offsets
    tag_table_start = 132  # 128 header + 4 count
    data_start = tag_table_start + tag_count * 12
    current_offset = data_start
    tag_entries = bytearray()
    tag_data = bytearray()

    for sig, data in tags.items():
        tag_entries += sig
        tag_entries += struct.pack(">I", current_offset)
        tag_entries += struct.pack(">I", len(data))
        tag_data += data
        # Pad to 4-byte boundary
        pad = (4 - len(data) % 4) % 4
        tag_data += b"\x00" * pad
        current_offset += len(data) + pad

    profile = bytes(header) + tag_dir + bytes(tag_entries) + bytes(tag_data)

    # Fix size in header
    profile = struct.pack(">I", len(profile)) + profile[4:]

    return profile


class TestIccTagParsing:
    def test_extract_tags_from_minimal_profile(self):
        profile = _build_minimal_icc()
        result = extract_icc_tags(profile)
        assert result["tag_count"] == 9
        assert "desc" in result["tags"]
        assert "wtpt" in result["tags"]
        assert "cprt" in result["tags"]
        assert len(result["errors"]) == 0

    def test_required_tags_present(self):
        profile = _build_minimal_icc()
        result = extract_icc_tags(profile)
        assert "desc" in result["required_tags_present"]
        assert "wtpt" in result["required_tags_present"]
        assert len(result["required_tags_missing"]) == 0

    def test_required_tags_missing(self):
        # Build with only desc, omitting wtpt and cprt
        tags = {
            b"desc": b"desc" + b"\x00" * 4 + struct.pack(">I", 5) + b"Test\x00",
        }
        profile = _build_minimal_icc(tags=tags)
        result = extract_icc_tags(profile)
        assert "wtpt" in result["required_tags_missing"]
        assert "cprt" in result["required_tags_missing"]

    def test_xyz_type_parsing(self):
        profile = _build_minimal_icc()
        result = extract_icc_tags(profile)
        wtpt = result["tags"].get("wtpt", {})
        assert "xyz" in wtpt
        xyz = wtpt["xyz"]
        assert abs(xyz[0] - 0.9642) < 0.01
        assert abs(xyz[1] - 1.0) < 0.01

    def test_curve_type_parsing(self):
        profile = _build_minimal_icc()
        result = extract_icc_tags(profile)
        rtrc = result["tags"].get("rTRC", {})
        assert rtrc.get("type") == "curveType"
        assert abs(rtrc.get("gamma", 0) - 2.2) < 0.1


class TestValidateIccProfileBytes:
    def test_valid_profile(self):
        profile = _build_minimal_icc()
        result = validate_icc_profile_bytes(profile)
        assert result["valid"] is True
        assert result["metadata"]["version"] == "4.0"
        assert result["metadata"]["rendering_intent"] == "Perceptual"

    def test_version_extraction(self):
        profile = _build_minimal_icc(version_major=2, version_minor=4)
        result = validate_icc_profile_bytes(profile)
        assert result["metadata"]["version"] == "2.4"
        assert result["metadata"]["version_major"] == 2
        assert result["metadata"]["version_minor"] == 4

    def test_rendering_intent(self):
        profile = _build_minimal_icc(rendering_intent=2)
        result = validate_icc_profile_bytes(profile)
        assert result["metadata"]["rendering_intent"] == "Saturation"
        assert result["metadata"]["rendering_intent_code"] == 2

    def test_pcs_illuminant_valid(self):
        profile = _build_minimal_icc()
        result = validate_icc_profile_bytes(profile)
        assert result["pcs_illuminant_valid"] is True

    def test_pcs_illuminant_invalid(self):
        profile = _build_minimal_icc(d50_x=1.0, d50_y=1.0, d50_z=1.0)
        result = validate_icc_profile_bytes(profile)
        assert result["pcs_illuminant_valid"] is False
        assert result["pcs_illuminant"]["X"] > 0.98

    def test_too_small_profile(self):
        result = validate_icc_profile_bytes(b"\x00" * 50)
        assert result["valid"] is False
        assert "too small" in result["error"]

    def test_invalid_magic(self):
        profile = bytearray(128)
        struct.pack_into(">I", profile, 0, 128)
        result = validate_icc_profile_bytes(bytes(profile))
        assert result["valid"] is False
        assert "magic" in result["error"]


class TestIccAnalyzerNewChecks:
    def test_icc_007_missing_tags(self):
        """GRD_ICC_007 fires when required tags are missing."""
        tags = {
            b"desc": b"desc" + b"\x00" * 4 + struct.pack(">I", 5) + b"Test\x00",
        }
        profile = _build_minimal_icc(tags=tags)
        cs = PdfColorSpace(
            name="CS1",
            cs_type="ICCBased",
            components=3,
            icc_profile_ref="profile_1",
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer(
            icc_profile_bytes_map={"profile_1": profile},
        )
        findings = analyzer.analyze(doc, [])
        icc_007 = [f for f in findings if f.inspection_id == "GRD_ICC_007"]
        assert len(icc_007) >= 1
        assert icc_007[0].severity == Severity.SQUALL

    def test_icc_007_no_fire_when_complete(self):
        """GRD_ICC_007 does not fire when all required tags present."""
        profile = _build_minimal_icc()
        cs = PdfColorSpace(
            name="CS1",
            cs_type="ICCBased",
            components=3,
            icc_profile_ref="profile_1",
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer(
            icc_profile_bytes_map={"profile_1": profile},
        )
        findings = analyzer.analyze(doc, [])
        icc_007 = [f for f in findings if f.inspection_id == "GRD_ICC_007"]
        assert len(icc_007) == 0

    def test_icc_009_bad_illuminant(self):
        """GRD_ICC_009 fires when PCS illuminant is not D50."""
        profile = _build_minimal_icc(d50_x=1.0, d50_y=1.0, d50_z=1.0)
        cs = PdfColorSpace(
            name="CS1",
            cs_type="ICCBased",
            components=3,
            icc_profile_ref="profile_1",
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer(
            icc_profile_bytes_map={"profile_1": profile},
        )
        findings = analyzer.analyze(doc, [])
        icc_009 = [f for f in findings if f.inspection_id == "GRD_ICC_009"]
        assert len(icc_009) >= 1
        assert icc_009[0].severity == Severity.SQUALL

    def test_icc_009_no_fire_when_d50(self):
        """GRD_ICC_009 does not fire with correct D50 illuminant."""
        profile = _build_minimal_icc()
        cs = PdfColorSpace(
            name="CS1",
            cs_type="ICCBased",
            components=3,
            icc_profile_ref="profile_1",
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer(
            icc_profile_bytes_map={"profile_1": profile},
        )
        findings = analyzer.analyze(doc, [])
        icc_009 = [f for f in findings if f.inspection_id == "GRD_ICC_009"]
        assert len(icc_009) == 0
