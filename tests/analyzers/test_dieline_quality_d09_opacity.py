"""Tests for D-09 → LPDF_DIE_OPACITY_LOW (dieline opacity < 100%).

Path A net-new check. Same failure surface as D-08 — the cutter
spot is a layer-extracted process control, not artwork, so partial
alpha doesn't survive RIP separation. ISO 32000-2:2020 §11.6.4.4
+ ISO 19593-1 §5.3.
"""

from __future__ import annotations

import io

import pikepdf

from siftpdf.analyzers.dieline_quality import check_dieline_quality
from siftpdf.analyzers.finding import Severity


def _build_pdf(
    content: bytes,
    extgstate_entries: dict[str, dict[str, object]] | None = None,
) -> bytes:
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


def test_dieline_stroke_with_ca_50pct_fires() -> None:
    """gs sets /CA=0.5; stroke dieline → emits LPDF_DIE_OPACITY_LOW."""
    content = b"/GS_HALF gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_HALF": {"CA": 0.5}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    op = _filter(findings, "LPDF_DIE_OPACITY_LOW")
    assert len(op) == 1
    f = op[0]
    assert f.severity == Severity.WARNING
    assert f.details["spot_name"] == "Dieline"
    assert f.details["violation_count"] == 1
    assert f.details["min_alpha"] == 0.5
    assert f.details["min_alpha_pct"] == 50.0


def test_dieline_fill_with_ca_lower_20pct_fires() -> None:
    """gs sets /ca=0.2; fill dieline → fires."""
    content = b"/GS_LOW gs\n/CS_DIE cs\n1 scn\n100 100 200 200 re\nf\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_LOW": {"ca": 0.2}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    op = _filter(findings, "LPDF_DIE_OPACITY_LOW")
    assert len(op) == 1
    assert op[0].details["min_alpha_pct"] == 20.0


def test_min_alpha_tracks_worst_seen() -> None:
    """When two violations exist, ``min_alpha`` is the lowest of them."""
    content = (
        b"/GS_70 gs\n"
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 100 50 50 re\n"
        b"S\n"
        b"/GS_30 gs\n"
        b"200 200 50 50 re\n"
        b"S\n"
        b"/GS_70 gs\n"
        b"300 300 50 50 re\n"
        b"S\n"
    )
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={
            "GS_70": {"CA": 0.7},
            "GS_30": {"CA": 0.3},
        },
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    op = _filter(findings, "LPDF_DIE_OPACITY_LOW")
    assert len(op) == 1
    assert op[0].details["violation_count"] == 3
    assert op[0].details["min_alpha"] == 0.3


def test_combined_op_takes_worst_of_stroke_and_fill() -> None:
    """B operator both strokes and fills → effective alpha is min(CA, ca)."""
    content = b"/GS_MIX gs\n/CS_DIE CS\n/CS_DIE cs\n1 SCN\n1 scn\n100 100 200 200 re\nB\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_MIX": {"CA": 0.9, "ca": 0.4}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    op = _filter(findings, "LPDF_DIE_OPACITY_LOW")
    assert len(op) == 1
    assert op[0].details["min_alpha"] == 0.4


# ────────────────────────────────────────────────────────────────────
# Negative — silent
# ────────────────────────────────────────────────────────────────────


def test_dieline_stroke_at_full_opacity_silent() -> None:
    """/CA=1.0 explicit (default) → no fire."""
    content = b"/GS_FULL gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_FULL": {"CA": 1.0}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_OPACITY_LOW") == []


def test_dieline_no_extgstate_silent() -> None:
    """No gs op at all → defaults to CA=ca=1.0 → silent."""
    content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(content)
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_OPACITY_LOW") == []


def test_non_dieline_paint_with_low_alpha_silent() -> None:
    """Reduced opacity on non-dieline artwork is the artwork's problem."""
    content = b"/GS_HALF gs\n/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_HALF": {"ca": 0.5}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_OPACITY_LOW") == []


def test_no_spot_name_silent() -> None:
    """Missing dieline detection precondition → no D-09 emission."""
    content = b"/GS_HALF gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_HALF": {"CA": 0.5}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
    assert _filter(findings, "LPDF_DIE_OPACITY_LOW") == []


def test_stroke_op_only_consults_stroke_alpha() -> None:
    """Stroke-only op (S) with /ca=0.2 but /CA=1.0 → silent.

    The fill-alpha drop doesn't apply to a stroke-only op.
    """
    content = b"/GS_FILL_LOW gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_FILL_LOW": {"CA": 1.0, "ca": 0.2}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    assert _filter(findings, "LPDF_DIE_OPACITY_LOW") == []


# ────────────────────────────────────────────────────────────────────
# q/Q save-restore
# ────────────────────────────────────────────────────────────────────


def test_save_restore_isolates_alpha() -> None:
    """Alpha set inside q/Q must not leak after Q.

    stroke#1 (default 1.0 — silent) → q → /CA=0.5 → stroke#2 (fires) →
    Q → stroke#3 (1.0 again — silent). One violation total.
    """
    content = (
        b"/CS_DIE CS\n"
        b"1 SCN\n"
        b"100 100 50 50 re\n"
        b"S\n"
        b"q\n"
        b"/GS_HALF gs\n"
        b"200 200 50 50 re\n"
        b"S\n"
        b"Q\n"
        b"300 300 50 50 re\n"
        b"S\n"
    )
    pdf_bytes = _build_pdf(
        content,
        extgstate_entries={"GS_HALF": {"CA": 0.5}},
    )
    findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
    op = _filter(findings, "LPDF_DIE_OPACITY_LOW")
    assert len(op) == 1
    assert op[0].details["violation_count"] == 1
    assert op[0].details["min_alpha"] == 0.5


# ────────────────────────────────────────────────────────────────────
# CheckInfo registration
# ────────────────────────────────────────────────────────────────────


def test_checkinfo_registered_with_v2_id() -> None:
    """Reports must surface D-09 as the v2 ID for LPDF_DIE_OPACITY_LOW."""
    from siftpdf.reports.check_names import CHECK_NAMES

    info = CHECK_NAMES["LPDF_DIE_OPACITY_LOW"]
    assert info.name == "Dieline Has Reduced Opacity"
    assert info.v2_ids == ("D-09",)
