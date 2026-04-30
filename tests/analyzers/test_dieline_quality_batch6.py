"""Tests for Batch 6 dieline-quality findings.

Covers:
  - T3-D04 → LPDF_DIE_EXCESSIVE_BLEED (paint overhang exceeds
    max_bleed_mm past the dieline envelope)

T3-D12 (LPDF_INK_SUBSTRATE) lives in ink_coverage_analyzer.py and is
tested separately in test_ink_substrate.py.

T3-D13 (fine multi-ink vector registration risk) is already covered
by LPDF_STROKE_004 and LPDF_STROKE_007 — see T3-D13/design.md.
"""

from __future__ import annotations

import io

import pikepdf
import pytest

from siftpdf.analyzers.dieline_quality import check_dieline_quality
from siftpdf.analyzers.finding import Severity


def _build_pdf(content: bytes) -> bytes:
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


class TestExcessiveBleed:
    @staticmethod
    def test_excessive_overhang_fires() -> None:
        """Dieline is 100x100 at (50,50). Paint at (40,40,120x120) —
        overhangs by 10pt on each side ≈ 3.5mm. With max_bleed_mm=2mm,
        this fires (overhang > max_bleed_mm)."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n40 40 120 120 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            max_bleed_mm=2.0,  # 2mm = ~5.67pt
        )
        excessive = [f for f in findings if f.inspection_id == "LPDF_DIE_EXCESSIVE_BLEED"]
        assert len(excessive) == 1
        f = excessive[0]
        assert f.severity == Severity.ADVISORY
        assert f.details["excessive_count"] == 1
        assert f.details["max_overhang_mm"] > 2.0
        assert f.details["max_bleed_mm"] == 2.0

    @staticmethod
    def test_within_max_bleed_silent() -> None:
        """2mm overhang with 5mm max_bleed → silent."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n44 44 112 112 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            max_bleed_mm=5.0,
        )
        excessive = [f for f in findings if f.inspection_id == "LPDF_DIE_EXCESSIVE_BLEED"]
        assert excessive == []

    @staticmethod
    def test_max_bleed_none_silent() -> None:
        """max_bleed_mm absent → check disabled → silent."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n0 0 500 500 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            max_bleed_mm=None,
        )
        excessive = [f for f in findings if f.inspection_id == "LPDF_DIE_EXCESSIVE_BLEED"]
        assert excessive == []

    @staticmethod
    def test_no_regions_silent() -> None:
        content = b"/DeviceRGB cs\n1 0 0 scn\n0 0 500 500 re\nf\n"
        pdf_bytes = _build_pdf(content)
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=None,
            max_bleed_mm=2.0,
        )
        excessive = [f for f in findings if f.inspection_id == "LPDF_DIE_EXCESSIVE_BLEED"]
        assert excessive == []

    @staticmethod
    def test_coexists_with_content_outside() -> None:
        """A paint that overhangs by a lot triggers BOTH T3-D05 and
        T3-D04 — they're complementary."""
        content = b"/DeviceRGB cs\n1 0 0 scn\n0 0 500 500 re\nf\n"
        pdf_bytes = _build_pdf(content)
        regions = [{"x0": 50.0, "y0": 50.0, "x1": 150.0, "y1": 150.0}]
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            regions=regions,
            max_bleed_mm=2.0,
        )
        ids = {f.inspection_id for f in findings}
        assert "LPDF_DIE_CONTENT_OUTSIDE" in ids
        assert "LPDF_DIE_EXCESSIVE_BLEED" in ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
