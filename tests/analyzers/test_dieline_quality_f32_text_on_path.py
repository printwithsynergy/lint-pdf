"""Tests for F-32 → LPDF_TEXT_ON_DIELINE_PATH (text overlaps cut path).

Path A net-new check. Distinct from LPDF_TEXT_NEAR_FOLD (clearance) —
F-32 fires on actual bbox intersection between text and the dieline
spot's stroke path. ISO 19593-1 §5.3 / cut-path clearance.
"""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.dieline_quality import check_dieline_quality
from lintpdf.analyzers.finding import Severity


def _build_pdf(content: bytes) -> bytes:
    """Single-page PDF with the standard /CS_DIE Separation
    pointing at the ``Dieline`` colourant + a Helvetica font."""
    pdf = pikepdf.new()
    tint_xform = pdf.make_indirect(
        pikepdf.Dictionary(
            FunctionType=2,
            Domain=pikepdf.Array([0, 1]),
            Range=pikepdf.Array([0, 1, 0, 1, 0, 1, 0, 1]),
            C0=pikepdf.Array([0, 0, 0, 0]),
            C1=pikepdf.Array([0, 0, 0, 1]),
            N=1,
        )
    )
    sep_cs = pikepdf.Array(
        [
            pikepdf.Name("/Separation"),
            pikepdf.Name("/Dieline"),
            pikepdf.Name("/DeviceCMYK"),
            tint_xform,
        ]
    )
    font = pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"),
        Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding"),
    )
    resources = pikepdf.Dictionary(
        ColorSpace=pikepdf.Dictionary(CS_DIE=sep_cs),
        Font=pikepdf.Dictionary(F1=font),
    )
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _filter(findings: list, inspection_id: str) -> list:
    return [f for f in findings if f.inspection_id == inspection_id]


# ────────────────────────────────────────────────────────────────────
# Positive — text overlaps the dieline stroke
# ────────────────────────────────────────────────────────────────────


def test_text_intersecting_dieline_stroke_fires() -> None:
    """Stroke a horizontal dieline at y=200 spanning x=100..400, then
    render text at the same y — the text bbox overlaps the stroke bbox.
    """
    content = (
        # Stroke a wide rectangle in the dieline spot; the stroke bbox
        # spans the whole rectangle outline.
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 195 300 10 re\n"
        b"S\n"
        # Text drawn in the middle of that stroke bbox.
        b"BT\n"
        b"/F1 12 Tf\n"
        b"150 200 Td\n"
        b"(SLICE) Tj\n"
        b"ET\n"
    )
    findings = check_dieline_quality(_build_pdf(content), spot_name="Dieline", source="name")
    on_path = _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH")
    assert len(on_path) == 1
    f = on_path[0]
    assert f.severity == Severity.WARNING
    assert f.details["spot_name"] == "Dieline"
    assert f.details["text_count"] == 1
    assert f.details["worst_overlap_pts2"] > 0


def test_multiple_text_regions_aggregated() -> None:
    """Two text strings both overlap the dieline → text_count == 2."""
    content = (
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 195 400 10 re\n"
        b"S\n"
        b"BT /F1 12 Tf 150 200 Td (FOO) Tj ET\n"
        b"BT /F1 12 Tf 300 200 Td (BAR) Tj ET\n"
    )
    findings = check_dieline_quality(_build_pdf(content), spot_name="Dieline", source="name")
    on_path = _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH")
    assert len(on_path) == 1
    assert on_path[0].details["text_count"] >= 2


# ────────────────────────────────────────────────────────────────────
# Negative — text clear of dieline
# ────────────────────────────────────────────────────────────────────


def test_text_clear_of_dieline_silent() -> None:
    """Text painted far from the dieline → no fire."""
    content = b"/CS_DIE CS\n1 SCN\n100 195 300 10 re\nS\nBT /F1 12 Tf 150 500 Td (SAFE) Tj ET\n"
    findings = check_dieline_quality(_build_pdf(content), spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH") == []


def test_no_text_silent() -> None:
    """Stroke present but no text → no fire."""
    content = b"/CS_DIE CS\n1 SCN\n100 195 300 10 re\nS\n"
    findings = check_dieline_quality(_build_pdf(content), spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH") == []


def test_no_dieline_stroke_silent() -> None:
    """Text but no dieline stroke → no fire."""
    content = b"BT /F1 12 Tf 150 200 Td (HELLO) Tj ET\n"
    findings = check_dieline_quality(_build_pdf(content), spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH") == []


def test_no_spot_name_silent() -> None:
    """Without a resolved dieline spot, F-32 cannot bind the cut path."""
    content = b"/CS_DIE CS\n1 SCN\n100 195 300 10 re\nS\nBT /F1 12 Tf 150 200 Td (TEXT) Tj ET\n"
    findings = check_dieline_quality(_build_pdf(content), spot_name=None, source="name")
    assert _filter(findings, "LPDF_TEXT_ON_DIELINE_PATH") == []


# ────────────────────────────────────────────────────────────────────
# CheckInfo registration
# ────────────────────────────────────────────────────────────────────


def test_checkinfo_registered_with_v2_id() -> None:
    """Reports must surface F-32 as the v2 ID for the new check."""
    from lintpdf.reports.check_names import CHECK_NAMES

    info = CHECK_NAMES["LPDF_TEXT_ON_DIELINE_PATH"]
    assert info.name == "Text Overlaps Dieline Cut Path"
    assert info.v2_ids == ("F-32",)
