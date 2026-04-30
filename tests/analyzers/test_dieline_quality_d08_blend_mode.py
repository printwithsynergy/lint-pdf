"""Tests for D-08 → LPDF_DIE_BLEND_MODE (dieline non-Normal blend mode).

Path A marketing-fix exemplar. The cutter spot is a layer-extracted
process control, not artwork — any blend mode other than Normal will
not survive RIP separation. ISO 32000-2:2020 §11.6.2 +
ISO 19593-1 §5.3.

Uses hand-crafted PDFs built with pikepdf so the tests exercise the
full content-stream walker.
"""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.dieline_quality import check_dieline_quality
from lintpdf.analyzers.finding import Severity


def _build_pdf(
    content: bytes,
    extgstate_entries: dict[str, dict[str, object]] | None = None,
) -> bytes:
    """Build a minimal single-page PDF.

    ``extgstate_entries`` maps ``GSName -> dict`` so callers can register
    e.g. ``{"GS_BM_MULT": {"BM": pikepdf.Name("/Multiply")}}`` and refer
    to it from the content stream as ``/GS_BM_MULT gs``.
    """
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
    resources = pikepdf.Dictionary(
        ColorSpace=pikepdf.Dictionary(CS_DIE=sep_cs),
    )
    if extgstate_entries:
        gs_dict = pikepdf.Dictionary()
        for name, entries in extgstate_entries.items():
            gs_dict[f"/{name}"] = pikepdf.Dictionary(**entries)
        resources["/ExtGState"] = gs_dict
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _filter(findings: list, inspection_id: str) -> list:
    return [f for f in findings if f.inspection_id == inspection_id]


# ────────────────────────────────────────────────────────────────────
# Positive — fires
# ────────────────────────────────────────────────────────────────────


def test_dieline_stroke_with_multiply_fires() -> None:
    """gs /GS_MULT then stroke dieline → emits LPDF_DIE_BLEND_MODE."""
    content = b"/GS_MULT gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_MULT": {"BM": pikepdf.Name("/Multiply")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    bm_findings = _filter(findings, "LPDF_DIE_BLEND_MODE")
    assert len(bm_findings) == 1
    f = bm_findings[0]
    assert f.severity == Severity.WARNING
    assert f.details["spot_name"] == "Dieline"
    assert f.details["violation_count"] == 1
    assert f.details["blend_modes"] == ["Multiply"]
    assert f.details["first_violation_op_idx"] >= 0


def test_dieline_fill_with_darken_fires() -> None:
    """Fill in dieline spot with BM=Darken still trips D-08."""
    content = b"/GS_DARK gs\n/CS_DIE cs\n1 scn\n100 100 200 200 re\nf\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_DARK": {"BM": pikepdf.Name("/Darken")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    bm_findings = _filter(findings, "LPDF_DIE_BLEND_MODE")
    assert len(bm_findings) == 1
    assert bm_findings[0].details["blend_modes"] == ["Darken"]


def test_multiple_violations_dedup_and_sort_modes() -> None:
    """Two violations with two different non-Normal modes → unique, sorted."""
    content = (
        b"/GS_SCREEN gs\n"
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 100 50 50 re\n"
        b"S\n"
        b"/GS_MULT gs\n"
        b"200 200 50 50 re\n"
        b"S\n"
        b"/GS_SCREEN gs\n"
        b"300 300 50 50 re\n"
        b"S\n"
    )
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={
            "GS_MULT": {"BM": pikepdf.Name("/Multiply")},
            "GS_SCREEN": {"BM": pikepdf.Name("/Screen")},
        },
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    bm = _filter(findings, "LPDF_DIE_BLEND_MODE")
    assert len(bm) == 1
    assert bm[0].details["violation_count"] == 3
    assert bm[0].details["blend_modes"] == ["Multiply", "Screen"]


# ────────────────────────────────────────────────────────────────────
# Negative — silent
# ────────────────────────────────────────────────────────────────────


def test_dieline_stroke_with_explicit_normal_silent() -> None:
    """gs setting BM=Normal explicitly is the default and must not fire."""
    content = b"/GS_NORM gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_NORM": {"BM": pikepdf.Name("/Normal")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_BLEND_MODE") == []


def test_dieline_stroke_no_extgstate_silent() -> None:
    """No gs op at all → default Normal → silent."""
    content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(content)
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_BLEND_MODE") == []


def test_non_dieline_paint_with_multiply_silent() -> None:
    """Multiply on non-dieline artwork is not the cutter plate's problem."""
    content = b"/GS_MULT gs\n/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_MULT": {"BM": pikepdf.Name("/Multiply")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_BLEND_MODE") == []


def test_no_spot_name_silent() -> None:
    """Missing dieline detection precondition → no D-08 emission."""
    content = b"/GS_MULT gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_MULT": {"BM": pikepdf.Name("/Multiply")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
    assert _filter(findings, "LPDF_DIE_BLEND_MODE") == []


# ────────────────────────────────────────────────────────────────────
# q/Q save-restore correctness
# ────────────────────────────────────────────────────────────────────


def test_save_restore_isolates_blend_mode() -> None:
    """Multiply set inside q/Q must not leak after Q.

    Sequence: stroke#1 (Normal — pre q) → q → gs Multiply → stroke#2
    (Multiply — fires) → Q → stroke#3 (Normal again — silent).
    Only one violation is recorded.
    """
    content = (
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 100 50 50 re\n"
        b"S\n"
        b"q\n"
        b"/GS_MULT gs\n"
        b"200 200 50 50 re\n"
        b"S\n"
        b"Q\n"
        b"300 300 50 50 re\n"
        b"S\n"
    )
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_MULT": {"BM": pikepdf.Name("/Multiply")}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    bm = _filter(findings, "LPDF_DIE_BLEND_MODE")
    assert len(bm) == 1
    assert bm[0].details["violation_count"] == 1
    assert bm[0].details["blend_modes"] == ["Multiply"]


# ────────────────────────────────────────────────────────────────────
# CheckInfo registration
# ────────────────────────────────────────────────────────────────────


def test_checkinfo_registered_with_v2_id() -> None:
    """Reports must surface D-08 as the v2 ID for LPDF_DIE_BLEND_MODE."""
    from lintpdf.reports.check_names import CHECK_NAMES

    info = CHECK_NAMES["LPDF_DIE_BLEND_MODE"]
    assert info.name == "Dieline Has Non-Normal Blend Mode"
    assert info.v2_ids == ("D-08",)
