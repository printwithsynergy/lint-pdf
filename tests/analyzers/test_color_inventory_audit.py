"""Unit tests for PR-K color inventory audit checks."""

from __future__ import annotations

from siftpdf.analyzers.color_inventory_audit import ColorInventoryAuditAnalyzer
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(color_spaces: dict[str, PdfColorSpace]) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _sep(name: str, idx: int = 0) -> tuple[str, PdfColorSpace]:
    cs = PdfColorSpace(
        name=f"CS{idx}",
        cs_type="Separation",
        components=1,
        colorant_names=(name,),
    )
    return f"CS{idx}", cs


def _devicen(cs_name: str, colorants: tuple[str, ...]) -> tuple[str, PdfColorSpace]:
    cs = PdfColorSpace(
        name=cs_name,
        cs_type="DeviceN",
        components=len(colorants),
        colorant_names=colorants,
    )
    return cs_name, cs


def _cmyk_cs(name: str = "CMYK") -> tuple[str, PdfColorSpace]:
    cs = PdfColorSpace(name=name, cs_type="DeviceCMYK", components=4)
    return name, cs


# ── LPDF_COLOR_PLATE_COUNT_HIGH ────────────────────────────────────


def test_six_or_fewer_plates_no_finding() -> None:
    spaces = dict([_cmyk_cs(), _sep("PMS185", 0), _sep("PMS200", 1)])  # 4 + 2 = 6
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_PLATE_COUNT_HIGH"]


def test_seven_plates_fires_advisory() -> None:
    # CMYK + 3 spots = 7 plates → fire.
    spaces = dict([_cmyk_cs(), _sep("PMS185", 0), _sep("PMS200", 1), _sep("PMS400", 2)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    high = [x for x in findings if x.inspection_id == "LPDF_COLOR_PLATE_COUNT_HIGH"]
    assert len(high) == 1
    assert high[0].details["total_plates"] == 7


def test_processing_step_spots_excluded_from_count() -> None:
    """Cutting / Perforating / Crease are technical inks routed to
    finishing tools, not press stations."""
    spaces = dict(
        [
            _cmyk_cs(),
            _sep("PMS185", 0),
            _sep("PMS200", 1),
            _sep("Cutting", 2),  # ProcessingStep — excluded
            _sep("Perforating", 3),  # ProcessingStep — excluded
        ]
    )
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_PLATE_COUNT_HIGH"]


# ── LPDF_COLOR_DUPLICATE_K_SPOT ────────────────────────────────────


def test_black_black_spot_with_cmyk_fires() -> None:
    spaces = dict([_cmyk_cs(), _sep("Black Black", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    dup = [x for x in findings if x.inspection_id == "LPDF_COLOR_DUPLICATE_K_SPOT"]
    assert len(dup) == 1
    assert dup[0].details["spot_name"] == "Black Black"


def test_rich_black_spot_fires() -> None:
    spaces = dict([_cmyk_cs(), _sep("Rich Black", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert any(x.inspection_id == "LPDF_COLOR_DUPLICATE_K_SPOT" for x in findings)


def test_literal_black_spot_skipped_handled_elsewhere() -> None:
    """Plain '/Black' is covered by DuplicateProcessSpotAnalyzer; we
    don't double-flag it here."""
    spaces = dict([_cmyk_cs(), _sep("Black", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DUPLICATE_K_SPOT"]


def test_pms_spot_does_not_fire() -> None:
    spaces = dict([_cmyk_cs(), _sep("PMS Cool Gray 11", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DUPLICATE_K_SPOT"]


# ── LPDF_COLOR_DIELINE_PRINTABLE ───────────────────────────────────


def test_dieline_alone_fires() -> None:
    spaces = dict([_sep("Dieline", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    pr = [x for x in findings if x.inspection_id == "LPDF_COLOR_DIELINE_PRINTABLE"]
    assert len(pr) == 1


def test_dieline_with_cutting_step_no_finding() -> None:
    """When the doc has a Cutting / Perforating ProcessingStep alongside,
    the dieline is being routed to a finishing tool — don't flag."""
    spaces = dict([_sep("Dieline", 0), _sep("Cutting", 1)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DIELINE_PRINTABLE"]


def test_no_dieline_no_finding() -> None:
    spaces = dict([_cmyk_cs(), _sep("PMS185", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DIELINE_PRINTABLE"]


# ── LPDF_COLOR_DEVICEN_CMYK_NAMED ──────────────────────────────────


def test_devicen_with_cmyk_colorants_fires() -> None:
    spaces = dict([_devicen("CS2", ("Cyan", "Magenta", "Yellow", "Black", "PANTONE 225 C"))])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    n = [x for x in findings if x.inspection_id == "LPDF_COLOR_DEVICEN_CMYK_NAMED"]
    assert len(n) == 1
    assert "CS2" in n[0].details["devicen_color_spaces"]


def test_devicen_with_only_pantones_no_finding() -> None:
    spaces = dict([_devicen("CS3", ("PANTONE 185 C", "PANTONE 200 C"))])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DEVICEN_CMYK_NAMED"]


def test_separation_cyan_does_not_trigger_devicen_check() -> None:
    """The DeviceN check fires only for DeviceN/NChannel; Separation
    'Cyan' is a different problem (LPDF_SPOT_DUPE_PROCESS)."""
    spaces = dict([_sep("Cyan", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_DEVICEN_CMYK_NAMED"]


# ── LPDF_COLOR_ALL_SEPARATION (PR-T) ───────────────────────────────


def test_all_separation_fires() -> None:
    """Amalgam case: /All separation in colorant list."""
    spaces = dict([_cmyk_cs(), _sep("All", 0), _sep("PMS185", 1)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    f = [x for x in findings if x.inspection_id == "LPDF_COLOR_ALL_SEPARATION"]
    assert len(f) == 1
    assert f[0].details["colorant"] == "All"


def test_no_all_separation_no_finding() -> None:
    spaces = dict([_cmyk_cs(), _sep("PMS185", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_ALL_SEPARATION"]


# ── LPDF_COLOR_MIXED_SPOT_PROCESS (PR-T) ──────────────────────────


def test_one_spot_with_cmyk_fires() -> None:
    """Nutrops-style: 1 spot + CMYK process."""
    spaces = dict([_cmyk_cs(), _sep("PANTONE 2725 C", 0)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    f = [x for x in findings if x.inspection_id == "LPDF_COLOR_MIXED_SPOT_PROCESS"]
    assert len(f) == 1
    assert f[0].details["spot_inks"] == ["PANTONE 2725 C"]


def test_two_spots_with_cmyk_fires() -> None:
    """Nutrops_LS / Nutrops_SF case: 2 PMS spots + CMYK."""
    spaces = dict([_cmyk_cs(), _sep("PANTONE 2725 C", 0), _sep("PANTONE 7401 C", 1)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    f = [x for x in findings if x.inspection_id == "LPDF_COLOR_MIXED_SPOT_PROCESS"]
    assert len(f) == 1


def test_three_spots_with_cmyk_no_finding() -> None:
    """Multi-spot palette + process CMYK is the legitimate
    full-art case; don't flag."""
    spaces = dict(
        [
            _cmyk_cs(),
            _sep("PANTONE 185 C", 0),
            _sep("PANTONE 200 C", 1),
            _sep("PANTONE 400 C", 2),
        ]
    )
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_MIXED_SPOT_PROCESS"]


def test_spot_only_no_cmyk_no_finding() -> None:
    """Spot-only build (no DeviceCMYK) is fine."""
    spaces = dict([_sep("PANTONE 2725 C", 0), _sep("PANTONE 7401 C", 1)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_MIXED_SPOT_PROCESS"]


def test_processing_step_only_with_cmyk_no_finding() -> None:
    """Cutting / Perforating spots + CMYK is normal — those are
    technical inks, not press stations."""
    spaces = dict([_cmyk_cs(), _sep("Cutting", 0), _sep("Perforating", 1)])
    findings = ColorInventoryAuditAnalyzer().analyze(_doc(spaces), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_COLOR_MIXED_SPOT_PROCESS"]
