"""Tests for P-30 → LPDF_PAGE_BLEED_PAST_DIELINE.

Path A net-new check. Distinct from LPDF_DIE_EXCESSIVE_BLEED
(content overhang): P-30 catches a misconfigured bleed *allowance*
that doesn't fit within the cutter region. ISO 32000-2:2020 §14.11.2
+ ISO 19593-1 §5.3.
"""

from __future__ import annotations

from siftpdf.analyzers.dieline_quality import check_dieline_quality
from siftpdf.analyzers.finding import Severity

# Minimal valid PDF stream so check_dieline_quality's pdf_bytes guard passes.
# We don't actually need any specific content because the P-30 path runs
# AFTER the walker; a parsable PDF with a blank page is sufficient.
_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj <</Type/Catalog/Pages 2 0 R>> endobj\n"
    b"2 0 obj <</Type/Pages/Kids[3 0 R]/Count 1>> endobj\n"
    b"3 0 obj <</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<<>>"
    b"/Contents 4 0 R>> endobj\n"
    b"4 0 obj <</Length 0>> stream\n\nendstream endobj\n"
    b"xref\n0 5\n0000000000 65535 f\n"
    b"0000000009 00000 n\n0000000052 00000 n\n"
    b"0000000095 00000 n\n0000000188 00000 n\n"
    b"trailer <</Size 5/Root 1 0 R>>\n"
    b"startxref\n239\n%%EOF\n"
)


# Dieline envelope = a 100x100pt square centred at (200, 200).
_REGIONS_100PT = [{"x0": 150.0, "y0": 150.0, "x1": 250.0, "y1": 250.0}]


def _filter(findings: list, inspection_id: str) -> list:
    return [f for f in findings if f.inspection_id == inspection_id]


# ────────────────────────────────────────────────────────────────────
# Positive — fires
# ────────────────────────────────────────────────────────────────────


def test_bleedbox_extends_past_dieline_fires() -> None:
    """BleedBox 5pt larger than the envelope on every side → fires."""
    bleed_box = (145.0, 145.0, 255.0, 255.0)  # +5pt all around
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    p30 = _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE")
    assert len(p30) == 1
    f = p30[0]
    assert f.severity == Severity.WARNING
    assert f.details["overhang_pts"] == 5.0
    assert f.details["bleed_box_pts"] == [145.0, 145.0, 255.0, 255.0]
    assert f.details["dieline_envelope_pts"] == [150.0, 150.0, 250.0, 250.0]


def test_bleedbox_overhang_on_one_side_fires() -> None:
    """BleedBox extends past on the right edge only — still fires."""
    bleed_box = (150.0, 150.0, 270.0, 250.0)  # +20pt on x1
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    p30 = _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE")
    assert len(p30) == 1
    assert p30[0].details["overhang_pts"] == 20.0


def test_overhang_in_mm_rounded() -> None:
    """overhang_mm = overhang_pts x 0.352778 rounded to 3 dp."""
    bleed_box = (140.0, 150.0, 250.0, 250.0)  # +10pt on x0
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    p30 = _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE")
    assert len(p30) == 1
    assert p30[0].details["overhang_mm"] == round(10.0 * 0.352778, 3)


# ────────────────────────────────────────────────────────────────────
# Negative — silent
# ────────────────────────────────────────────────────────────────────


def test_bleedbox_inside_dieline_silent() -> None:
    """BleedBox snug inside dieline envelope → no fire."""
    bleed_box = (160.0, 160.0, 240.0, 240.0)  # 10pt inset
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


def test_bleedbox_overhang_under_tolerance_silent() -> None:
    """Sub-tolerance overhang is measurement noise — silent by default."""
    bleed_box = (149.5, 150.0, 250.0, 250.0)  # 0.5pt overhang on x0
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


def test_bleedbox_overhang_exactly_at_tolerance_silent() -> None:
    """1pt overhang at default 1pt tolerance → boundary, silent."""
    bleed_box = (149.0, 150.0, 250.0, 250.0)
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


def test_no_bleed_box_silent() -> None:
    """Caller didn't pass bleed_box → P-30 disabled."""
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=None,
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


def test_no_regions_silent() -> None:
    """No dieline regions → no envelope → silent (precondition unmet)."""
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=None,
        bleed_box=(140.0, 140.0, 260.0, 260.0),
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


def test_custom_tolerance_widens_silent_zone() -> None:
    """tolerance=10pt swallows up to 10pt of overhang."""
    bleed_box = (143.0, 150.0, 250.0, 250.0)  # 7pt overhang
    findings = check_dieline_quality(
        _PDF_BYTES,
        spot_name="Dieline",
        source="name",
        regions=_REGIONS_100PT,
        bleed_box=bleed_box,
        bleed_box_tolerance_pts=10.0,
    )
    assert _filter(findings, "LPDF_PAGE_BLEED_PAST_DIELINE") == []


# ────────────────────────────────────────────────────────────────────
# CheckInfo registration
# ────────────────────────────────────────────────────────────────────


def test_checkinfo_registered_with_v2_id() -> None:
    """Reports must surface P-30 as the v2 ID for the new check."""
    from siftpdf.reports.check_names import CHECK_NAMES

    info = CHECK_NAMES["LPDF_PAGE_BLEED_PAST_DIELINE"]
    assert info.name == "Page BleedBox Extends Past Dieline"
    assert info.v2_ids == ("P-30",)
