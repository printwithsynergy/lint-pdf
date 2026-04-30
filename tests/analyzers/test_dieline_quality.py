"""Tests for Batch 4 dieline-quality findings.

Covers:
  - T3-D02 → LPDF_DIE_ZORDER
  - T3-D03 → LPDF_DIE_KNOCKOUT
  - T3-D15 → LPDF_DIE_AS_ART

Uses hand-crafted PDF bytes built with pikepdf so the tests exercise
the full content-stream walker, not a mock.
"""

from __future__ import annotations

import io

import pikepdf
import pytest

from lintpdf.analyzers.dieline_quality import check_dieline_quality
from lintpdf.analyzers.finding import Severity


def _build_pdf_with_content_stream(
    content: bytes,
    extgstate: dict[str, object] | None = None,
) -> bytes:
    """Build a minimal single-page PDF whose page-1 content stream is
    ``content`` and whose resources declare a ``/CS_DIE`` Separation
    pointing at the ``Dieline`` colourant.
    """
    pdf = pikepdf.new()
    # Separation colour space: [/Separation /Dieline /DeviceCMYK <tintXform>]
    # Use a trivial identity-ish tint transform (Function 2 / exponential).
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
    if extgstate is not None:
        resources["/ExtGState"] = pikepdf.Dictionary(GS_OP=pikepdf.Dictionary(**extgstate))
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────────────
# Preconditions
# ────────────────────────────────────────────────────────────────────


class TestPreconditions:
    @staticmethod
    def test_missing_source_silent() -> None:
        assert check_dieline_quality(b"%PDF-1.6\n", spot_name="Dieline", source="missing") == []

    @staticmethod
    def test_no_spot_name_silent() -> None:
        assert check_dieline_quality(b"%PDF-1.6\n", spot_name=None, source="name") == []

    @staticmethod
    def test_empty_pdf_bytes_silent() -> None:
        assert check_dieline_quality(b"", spot_name="Dieline", source="name") == []

    @staticmethod
    def test_broken_pdf_silent() -> None:
        """Corrupt bytes should never raise — just return []."""
        assert check_dieline_quality(b"not-a-pdf", spot_name="Dieline", source="name") == []


# ────────────────────────────────────────────────────────────────────
# T3-D02 — z-order
# ────────────────────────────────────────────────────────────────────


class TestZOrder:
    @staticmethod
    def test_dieline_first_fires() -> None:
        """Paint dieline stroke FIRST, then non-dieline fill → z-order violation."""
        content = (
            # Stroke dieline rectangle
            b"/CS_DIE CS\n"
            b"1 SCN\n"
            b"100 100 200 200 re\n"
            b"S\n"
            # Then fill non-dieline rectangle
            b"/DeviceRGB cs\n"
            b"1 0 0 scn\n"
            b"150 150 100 100 re\n"
            b"f\n"
        )
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        zorder = [f for f in findings if f.inspection_id == "LPDF_DIE_ZORDER"]
        assert len(zorder) == 1
        f = zorder[0]
        assert f.severity == Severity.WARNING
        assert f.details["spot_name"] == "Dieline"
        assert f.details["last_dieline_paint_idx"] < f.details["last_nondieline_paint_idx"]

    @staticmethod
    def test_dieline_last_silent() -> None:
        """Non-dieline content first, dieline last → healthy stack → silent."""
        content = (
            b"/DeviceRGB cs\n"
            b"0 0 1 scn\n"
            b"150 150 100 100 re\n"
            b"f\n"
            b"/CS_DIE CS\n"
            b"1 SCN\n"
            b"100 100 200 200 re\n"
            b"S\n"
        )
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        zorder = [f for f in findings if f.inspection_id == "LPDF_DIE_ZORDER"]
        assert zorder == []

    @staticmethod
    def test_dieline_only_silent() -> None:
        """Dieline-only content stream → no zorder finding."""
        content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        zorder = [f for f in findings if f.inspection_id == "LPDF_DIE_ZORDER"]
        assert zorder == []


# ────────────────────────────────────────────────────────────────────
# T3-D03 — knockout
# ────────────────────────────────────────────────────────────────────


class TestKnockout:
    @staticmethod
    def test_default_op_false_fires() -> None:
        """No /OP set at all → defaults to false → dieline stroke fires."""
        content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        knockout = [f for f in findings if f.inspection_id == "LPDF_DIE_KNOCKOUT"]
        assert len(knockout) == 1
        assert knockout[0].severity == Severity.WARNING
        assert knockout[0].details["knockout_stroke_count"] == 1

    @staticmethod
    def test_op_true_via_extgstate_silent() -> None:
        """ExtGState with /OP true activated via `gs` op → silent."""
        content = b"/GS_OP gs\n/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
        pdf_bytes = _build_pdf_with_content_stream(content, extgstate={"OP": True})
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        knockout = [f for f in findings if f.inspection_id == "LPDF_DIE_KNOCKOUT"]
        assert knockout == []


# ────────────────────────────────────────────────────────────────────
# T3-D15 — used as art (fill)
# ────────────────────────────────────────────────────────────────────


class TestAsArt:
    @staticmethod
    def test_large_fill_fires_as_error() -> None:
        """Fill a 100x100pt rectangle with dieline spot → large area → error."""
        content = b"/CS_DIE cs\n1 scn\n100 100 100 100 re\nf\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        as_art = [f for f in findings if f.inspection_id == "LPDF_DIE_AS_ART"]
        assert len(as_art) == 1
        f = as_art[0]
        assert f.severity == Severity.ERROR
        assert f.details["fill_operator_count"] == 1
        assert f.details["is_large"] is True
        assert f.details["fill_area_pts2"] >= 50.0

    @staticmethod
    def test_tiny_fill_fires_as_advisory() -> None:
        """Fill a 5x5pt tick mark with dieline spot → below threshold → advisory."""
        content = b"/CS_DIE cs\n1 scn\n100 100 5 5 re\nf\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        as_art = [f for f in findings if f.inspection_id == "LPDF_DIE_AS_ART"]
        assert len(as_art) == 1
        assert as_art[0].severity == Severity.ADVISORY
        assert as_art[0].details["is_large"] is False

    @staticmethod
    def test_stroke_only_silent() -> None:
        """Dieline used as STROKE (not fill) → no as-art finding."""
        content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        as_art = [f for f in findings if f.inspection_id == "LPDF_DIE_AS_ART"]
        assert as_art == []


# ────────────────────────────────────────────────────────────────────
# Combined
# ────────────────────────────────────────────────────────────────────


class TestCombined:
    @staticmethod
    def test_multiple_findings_in_one_walk() -> None:
        """A PDF that's both zorder-wrong AND uses dieline as fill
        triggers BOTH findings in one invocation."""
        content = (
            # Dieline stroke first → zorder violation when non-dieline
            # follows.
            b"/CS_DIE CS\n"
            b"1 SCN\n"
            b"10 10 20 20 re\n"
            b"S\n"
            # Dieline fill → as-art.
            b"/CS_DIE cs\n"
            b"1 scn\n"
            b"100 100 100 100 re\n"
            b"f\n"
            # Non-dieline content at the end.
            b"/DeviceRGB cs\n"
            b"0 1 0 scn\n"
            b"500 500 50 50 re\n"
            b"f\n"
        )
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Dieline", source="name")
        ids = {f.inspection_id for f in findings}
        assert "LPDF_DIE_ZORDER" in ids
        assert "LPDF_DIE_AS_ART" in ids
        # Knockout also fires because no /OP was set anywhere.
        assert "LPDF_DIE_KNOCKOUT" in ids


# ────────────────────────────────────────────────────────────────────
# Spot-name mismatch
# ────────────────────────────────────────────────────────────────────


class TestSpotNameMismatch:
    @staticmethod
    def test_different_spot_name_silent() -> None:
        """Content uses /CS_DIE → Dieline spot. Caller asks for a
        different spot name → no findings. Confirms the spot-match
        logic isn't over-eager."""
        content = b"/CS_DIE CS\n1 SCN\n100 100 200 200 re\nS\n"
        pdf_bytes = _build_pdf_with_content_stream(content)
        findings = check_dieline_quality(pdf_bytes, spot_name="Perforation", source="name")
        assert findings == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
