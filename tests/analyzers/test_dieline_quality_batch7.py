"""Tests for Batch 7 dieline-quality findings (T3-D08, T3-D09).

T3-D11 lives in spot_name_normaliser.py — separate test file.
"""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.dieline_quality import check_dieline_quality
from lintpdf.analyzers.finding import Severity


def _make_sep_cs(spot_name: str, pdf: pikepdf.Pdf) -> pikepdf.Array:
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
    return pikepdf.Array(
        [
            pikepdf.Name("/Separation"),
            pikepdf.Name("/" + spot_name),
            pikepdf.Name("/DeviceCMYK"),
            tint_xform,
        ]
    )


def _build_pdf(content: bytes, *, spots: dict[str, str] | None = None) -> bytes:
    pdf = pikepdf.new()
    resources = pikepdf.Dictionary()
    if spots:
        cs_dict = pikepdf.Dictionary()
        for res_name, spot in spots.items():
            cs_dict[pikepdf.Name("/" + res_name)] = _make_sep_cs(spot, pdf)
        resources["/ColorSpace"] = cs_dict
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────────────
# T3-D08 — small dieline features
# ────────────────────────────────────────────────────────────────────


class TestSmallDielineFeatures:
    @staticmethod
    def test_tiny_polygon_fires() -> None:
        """A 0.5mm x 0.5mm polygon is well below the 1mm cutter threshold."""
        # 0.5mm ≈ 1.42pt
        polylines = [
            [
                [0.0, 0.0],
                [1.42, 0.0],
                [1.42, 1.42],
                [0.0, 1.42],
                [0.0, 0.0],
            ]
        ]
        findings = check_dieline_quality(
            _build_pdf(b""),
            spot_name="Dieline",
            source="name",
            polylines=polylines,
            min_dieline_feature_mm=1.0,
            min_dieline_segment_length_mm=1.0,
        )
        small = [f for f in findings if f.inspection_id == "LPDF_DIE_TOO_SMALL"]
        assert len(small) == 1
        f = small[0]
        assert f.severity == Severity.WARNING
        assert f.details["feature_count"] == 1
        assert f.details["smallest_width_mm"] < 1.0
        assert f.details["smallest_height_mm"] < 1.0

    @staticmethod
    def test_normal_polygon_silent() -> None:
        """A 50mm x 50mm polygon is way above threshold."""
        # 50mm ≈ 141.7pt
        polylines = [
            [
                [0.0, 0.0],
                [141.7, 0.0],
                [141.7, 141.7],
                [0.0, 141.7],
                [0.0, 0.0],
            ]
        ]
        findings = check_dieline_quality(
            _build_pdf(b""),
            spot_name="Dieline",
            source="name",
            polylines=polylines,
        )
        small = [f for f in findings if f.inspection_id == "LPDF_DIE_TOO_SMALL"]
        assert small == []

    @staticmethod
    def test_mixed_sizes_reports_smallest() -> None:
        polylines = [
            [[0, 0], [142, 0], [142, 142], [0, 142], [0, 0]],  # 50mm — fine
            [[300, 300], [301.5, 300], [301.5, 301.5], [300, 301.5], [300, 300]],  # 0.5mm
        ]
        findings = check_dieline_quality(
            _build_pdf(b""),
            spot_name="Dieline",
            source="name",
            polylines=polylines,
        )
        small = [f for f in findings if f.inspection_id == "LPDF_DIE_TOO_SMALL"]
        assert len(small) == 1
        assert small[0].details["feature_count"] == 1

    @staticmethod
    def test_no_polylines_silent() -> None:
        findings = check_dieline_quality(
            _build_pdf(b""),
            spot_name="Dieline",
            source="name",
            polylines=None,
        )
        small = [f for f in findings if f.inspection_id == "LPDF_DIE_TOO_SMALL"]
        assert small == []


# ────────────────────────────────────────────────────────────────────
# T3-D09 — white underprint coverage gap
# ────────────────────────────────────────────────────────────────────


class TestWhiteCoverageGap:
    @staticmethod
    def test_white_covers_full_dieline_silent() -> None:
        """White exactly covers the dieline → 100% coverage → silent."""
        content = b"/CS_WHITE cs\n1 scn\n50 50 100 100 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_WHITE": "OpaqueWhite"})
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
        )
        gap = [f for f in findings if f.inspection_id == "LPDF_DIE_WHITE_GAP"]
        assert gap == []

    @staticmethod
    def test_white_covers_partial_fires() -> None:
        """White covers ~50% of dieline area → fires."""
        content = b"/CS_WHITE cs\n1 scn\n50 50 50 100 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_WHITE": "OpaqueWhite"})
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            white_coverage_min=0.95,
        )
        gap = [f for f in findings if f.inspection_id == "LPDF_DIE_WHITE_GAP"]
        assert len(gap) == 1
        f = gap[0]
        assert f.severity == Severity.WARNING
        assert 40 < f.details["white_coverage_pct"] < 60
        assert f.details["white_spot"] == "OpaqueWhite"

    @staticmethod
    def test_no_white_spot_silent() -> None:
        """No white spot in resources → silent (precondition)."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n50 50 100 100 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
        )
        gap = [f for f in findings if f.inspection_id == "LPDF_DIE_WHITE_GAP"]
        assert gap == []

    @staticmethod
    def test_no_regions_silent() -> None:
        """No dieline polygon → silent."""
        content = b"/CS_WHITE cs\n1 scn\n0 0 50 50 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_WHITE": "White"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=None,
        )
        gap = [f for f in findings if f.inspection_id == "LPDF_DIE_WHITE_GAP"]
        assert gap == []

    @staticmethod
    def test_threshold_zero_disables() -> None:
        content = b"/CS_WHITE cs\n1 scn\n0 0 1 1 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_WHITE": "White"})
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            white_coverage_min=0.0,
        )
        gap = [f for f in findings if f.inspection_id == "LPDF_DIE_WHITE_GAP"]
        assert gap == []
