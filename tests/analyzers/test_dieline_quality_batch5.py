"""Tests for Batch 5 dieline-quality findings.

Covers:
  - T3-D01 → LPDF_DIE_LAYER_CONTENT (non-dieline paint inside
    dieline-named OCG)
  - T3-D05 → LPDF_DIE_CONTENT_OUTSIDE (paint bbox outside
    DielineResult.regions envelope)
  - T3-D10 → LPDF_DIE_VARNISH_COLLISION (varnish spot overlaps
    VarnishFree region)

Uses hand-crafted PDF bytes built with pikepdf so the tests exercise
the full content-stream walker, not a mock.
"""

from __future__ import annotations

import io

import pikepdf
import pytest

from siftpdf.analyzers.dieline_quality import (
    _is_dieline_name,
    _is_varnish_free_name,
    _is_varnish_name,
    check_dieline_quality,
)
from siftpdf.analyzers.finding import Severity


def _make_sep_cs(spot_name: str, pdf: pikepdf.Pdf) -> pikepdf.Array:
    """Build a minimal Separation colour space for ``spot_name``."""
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


def _build_pdf(
    content: bytes,
    *,
    spots: dict[str, str] | None = None,
    ocgs: dict[str, str] | None = None,
) -> bytes:
    """Build a minimal page PDF with:

    * ``spots`` — resource-name → Separation colourant name map.
      E.g. ``{"CS_DIE": "Dieline", "CS_VARN": "UV Varnish"}``.
    * ``ocgs`` — resource-name → OCG /Name label map.
      E.g. ``{"DielineOCG": "Dieline"}``.
    """
    pdf = pikepdf.new()
    resources = pikepdf.Dictionary()
    if spots:
        cs_dict = pikepdf.Dictionary()
        for res_name, spot in spots.items():
            cs_dict[pikepdf.Name("/" + res_name)] = _make_sep_cs(spot, pdf)
        resources["/ColorSpace"] = cs_dict
    if ocgs:
        props_dict = pikepdf.Dictionary()
        for res_name, name in ocgs.items():
            props_dict[pikepdf.Name("/" + res_name)] = pikepdf.Dictionary(
                Type=pikepdf.Name("/OCG"),
                Name=name,
            )
        resources["/Properties"] = props_dict
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────────────
# Spot-name classification helpers
# ────────────────────────────────────────────────────────────────────


class TestNameClassification:
    @staticmethod
    def test_dieline_names() -> None:
        assert _is_dieline_name("Dieline")
        assert _is_dieline_name("/CutContour")
        assert _is_dieline_name("Cut_Contour")
        assert _is_dieline_name("die-line")
        assert _is_dieline_name("PERFORATION")
        assert not _is_dieline_name("CMYK")
        assert not _is_dieline_name("Pantone 485 C")

    @staticmethod
    def test_varnish_names() -> None:
        assert _is_varnish_name("UV Varnish")
        assert _is_varnish_name("Gloss")
        assert _is_varnish_name("AquaCoat")
        assert _is_varnish_name("SpotUV")
        assert _is_varnish_name("varnish")
        assert not _is_varnish_name("Cyan")
        assert not _is_varnish_name("Dieline")

    @staticmethod
    def test_varnish_free_names() -> None:
        assert _is_varnish_free_name("VarnishFree")
        assert _is_varnish_free_name("Varnish Free")
        assert _is_varnish_free_name("NoVarnish")
        assert _is_varnish_free_name("no-coating")
        assert not _is_varnish_free_name("Varnish")  # not a free-marker
        assert not _is_varnish_free_name("Cyan")


# ────────────────────────────────────────────────────────────────────
# T3-D01 — content on dieline OCG
# ────────────────────────────────────────────────────────────────────


class TestLayerContent:
    @staticmethod
    def test_non_dieline_paint_in_dieline_ocg_fires() -> None:
        """Paint non-dieline content inside a Dieline-named OCG
        marked-content block → LPDF_DIE_LAYER_CONTENT fires."""
        content = b"/OC /DielineOCG BDC\n/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\nEMC\n"
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_DIE": "Dieline"},
            ocgs={"DielineOCG": "Dieline"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        layer = [f for f in findings if f.inspection_id == "LPDF_DIE_LAYER_CONTENT"]
        assert len(layer) == 1
        f = layer[0]
        assert f.severity == Severity.WARNING
        assert "Dieline" in f.details["ocg_names"]
        assert f.details["foreign_paint_count"] == 1

    @staticmethod
    def test_dieline_paint_in_dieline_ocg_silent() -> None:
        """Paint in dieline SPOT inside dieline OCG → healthy → silent."""
        content = b"/OC /DielineOCG BDC\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\nEMC\n"
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_DIE": "Dieline"},
            ocgs={"DielineOCG": "Dieline"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        layer = [f for f in findings if f.inspection_id == "LPDF_DIE_LAYER_CONTENT"]
        assert layer == []

    @staticmethod
    def test_non_dieline_paint_outside_ocg_silent() -> None:
        """Normal artwork with no OCG wrap → no layer finding."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_DIE": "Dieline"})
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        layer = [f for f in findings if f.inspection_id == "LPDF_DIE_LAYER_CONTENT"]
        assert layer == []

    @staticmethod
    def test_non_dieline_ocg_silent() -> None:
        """Non-dieline OCG (e.g., /BackgroundLayer) never triggers."""
        content = b"/OC /BackgroundOCG BDC\n/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\nEMC\n"
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_DIE": "Dieline"},
            ocgs={"BackgroundOCG": "Background"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        layer = [f for f in findings if f.inspection_id == "LPDF_DIE_LAYER_CONTENT"]
        assert layer == []


# ────────────────────────────────────────────────────────────────────
# T3-D05 — content outside dieline polygon
# ────────────────────────────────────────────────────────────────────


class TestContentOutside:
    @staticmethod
    def test_paint_outside_envelope_fires() -> None:
        """Dieline region is a 100x100 square at (50,50). Paint at
        (300,300 100x100) — far outside → fires."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n300 300 100 100 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
        )
        outside = [f for f in findings if f.inspection_id == "LPDF_DIE_CONTENT_OUTSIDE"]
        assert len(outside) == 1
        f = outside[0]
        assert f.severity == Severity.WARNING
        assert f.details["foreign_content_count"] == 1
        assert f.details["max_overhang_pts"] > 100

    @staticmethod
    def test_paint_inside_envelope_silent() -> None:
        """Paint fully within the dieline envelope → silent."""
        content = b"/DeviceRGB cs\n0 1 0 scn\n60 60 80 80 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
        )
        outside = [f for f in findings if f.inspection_id == "LPDF_DIE_CONTENT_OUTSIDE"]
        assert outside == []

    @staticmethod
    def test_within_tolerance_silent() -> None:
        """Paint 1pt outside the envelope at default 2.83pt tolerance
        → silent."""
        content = (
            b"/DeviceRGB cs\n"
            b"0 0 1 scn\n"
            b"49 49 102 102 re\n"  # 1pt overhang on all sides
            b"f\n"
        )
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
        )
        outside = [f for f in findings if f.inspection_id == "LPDF_DIE_CONTENT_OUTSIDE"]
        assert outside == []

    @staticmethod
    def test_no_regions_silent() -> None:
        """regions=None → check disabled → silent regardless of paint."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n300 300 100 100 re\nf\n"
        pdf_bytes = _build_pdf(content)
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=None,
        )
        outside = [f for f in findings if f.inspection_id == "LPDF_DIE_CONTENT_OUTSIDE"]
        assert outside == []


# ────────────────────────────────────────────────────────────────────
# T3-D10 — varnish / VarnishFree collision
# ────────────────────────────────────────────────────────────────────


class TestVarnishCollision:
    @staticmethod
    def test_overlapping_fires() -> None:
        """Varnish paints at (100,100,100x100) and VarnishFree paints at
        (150,150,100x100). Overlap is 50x50 = 2500pt² → fires."""
        content = (
            # Fill VarnishFree region first
            b"/CS_FREE cs\n"
            b"1 scn\n"
            b"150 150 100 100 re\n"
            b"f\n"
            # Paint varnish overlapping it
            b"/CS_VARN cs\n"
            b"1 scn\n"
            b"100 100 100 100 re\n"
            b"f\n"
        )
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_VARN": "UV Varnish", "CS_FREE": "VarnishFree"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
        varnish = [f for f in findings if f.inspection_id == "LPDF_DIE_VARNISH_COLLISION"]
        assert len(varnish) == 1
        f = varnish[0]
        assert f.severity == Severity.WARNING
        assert f.details["varnish_spot"] == "UV Varnish"
        assert f.details["varnish_free_spot"] == "VarnishFree"
        assert f.details["overlap_area_pts2"] >= 50.0

    @staticmethod
    def test_non_overlapping_silent() -> None:
        """Varnish at (100,100,50x50), VarnishFree at (300,300,50x50) →
        no overlap → silent."""
        content = (
            b"/CS_FREE cs\n1 scn\n300 300 50 50 re\nf\n/CS_VARN cs\n1 scn\n100 100 50 50 re\nf\n"
        )
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_VARN": "UV Varnish", "CS_FREE": "VarnishFree"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
        varnish = [f for f in findings if f.inspection_id == "LPDF_DIE_VARNISH_COLLISION"]
        assert varnish == []

    @staticmethod
    def test_only_varnish_silent() -> None:
        """Only Varnish spot, no VarnishFree → silent (no collision possible)."""
        content = b"/CS_VARN cs\n1 scn\n100 100 100 100 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_VARN": "UV Varnish"})
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
        varnish = [f for f in findings if f.inspection_id == "LPDF_DIE_VARNISH_COLLISION"]
        assert varnish == []

    @staticmethod
    def test_tiny_overlap_silent() -> None:
        """Overlap < 50pt² → below threshold → silent."""
        content = b"/CS_FREE cs\n1 scn\n100 100 5 5 re\nf\n/CS_VARN cs\n1 scn\n102 102 5 5 re\nf\n"
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_VARN": "UV Varnish", "CS_FREE": "VarnishFree"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="name")
        varnish = [f for f in findings if f.inspection_id == "LPDF_DIE_VARNISH_COLLISION"]
        assert varnish == []


# ────────────────────────────────────────────────────────────────────
# Source=missing precondition — Batch 5 findings also silent
# ────────────────────────────────────────────────────────────────────


class TestSourceMissing:
    @staticmethod
    def test_spot_findings_silent_when_missing() -> None:
        """Without spot_name, T3-D02/03/15 can't fire (they require a
        dieline spot). OCG-based T3-D01 can still fire if the marked
        content is on a dieline-named layer — same as it would when
        source='name' / 'vision'."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n100 100 200 200 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_DIE": "Dieline"})
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="missing")
        ids = {f.inspection_id for f in findings}
        # None of the spot-based checks fire without a spot.
        assert "LPDF_DIE_ZORDER" not in ids
        assert "LPDF_DIE_KNOCKOUT" not in ids
        assert "LPDF_DIE_AS_ART" not in ids
        # OCG / varnish / envelope checks are independent. With no
        # OCGs, no varnish spots, and no regions, nothing fires.
        assert findings == []

    @staticmethod
    def test_varnish_fires_without_dieline() -> None:
        """Varnish collision is independent of dieline detection —
        it can fire with spot_name=None and source='missing'."""
        content = (
            b"/CS_FREE cs\n1 scn\n150 150 100 100 re\nf\n"
            b"/CS_VARN cs\n1 scn\n100 100 100 100 re\nf\n"
        )
        pdf_bytes = _build_pdf(
            content,
            spots={"CS_VARN": "UV Varnish", "CS_FREE": "VarnishFree"},
        )
        findings = check_dieline_quality(pdf_bytes, spot_name=None, source="missing")
        ids = {f.inspection_id for f in findings}
        assert "LPDF_DIE_VARNISH_COLLISION" in ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
