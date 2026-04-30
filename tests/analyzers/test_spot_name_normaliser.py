"""Tests for T3-D11 LPDF_SPOT_NONCANONICAL — spot-name normaliser."""

from __future__ import annotations

import io

import pikepdf

from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.spot_name_normaliser import (
    CANONICAL_NAMES,
    check_spot_naming,
    find_canonical_name,
    normalise_spot_name,
)


def _build_pdf_with_spots(*spot_names: str) -> bytes:
    """Build a minimal PDF whose page resources declare each named
    spot as a Separation colour space."""
    pdf = pikepdf.new()
    cs_dict = pikepdf.Dictionary()
    for i, spot in enumerate(spot_names):
        tint = pdf.make_indirect(
            pikepdf.Dictionary(
                FunctionType=2,
                Domain=pikepdf.Array([0, 1]),
                Range=pikepdf.Array([0, 1, 0, 1, 0, 1, 0, 1]),
                C0=pikepdf.Array([0, 0, 0, 0]),
                C1=pikepdf.Array([0, 0, 0, 1]),
                N=1,
            )
        )
        cs_dict[pikepdf.Name(f"/CS{i}")] = pikepdf.Array(
            [
                pikepdf.Name("/Separation"),
                pikepdf.Name("/" + spot),
                pikepdf.Name("/DeviceCMYK"),
                tint,
            ]
        )
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = pikepdf.Dictionary(ColorSpace=cs_dict)
    page.Contents = pdf.make_stream(b"")
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


class TestNormalise:
    @staticmethod
    def test_lowercases() -> None:
        assert normalise_spot_name("CutContour") == "cutcontour"
        assert normalise_spot_name("/Dieline") == "dieline"

    @staticmethod
    def test_collapses_separators() -> None:
        assert normalise_spot_name("Cut_Contour") == "cut contour"
        assert normalise_spot_name("Cut-Line") == "cut line"
        assert normalise_spot_name("Cut  Line") == "cut line"


class TestFindCanonical:
    @staticmethod
    def test_canonical_passes_through() -> None:
        assert find_canonical_name("CutContour") == "CutContour"
        assert find_canonical_name("Varnish") == "Varnish"

    @staticmethod
    def test_variants_map_to_canonical() -> None:
        assert find_canonical_name("Cut Line") == "CutContour"
        assert find_canonical_name("DIE_CUT") == "CutContour"
        assert find_canonical_name("Trim") == "CutContour"
        assert find_canonical_name("FoldLine") == "Crease"
        assert find_canonical_name("Score") == "Crease"
        assert find_canonical_name("Perf") == "Perforation"
        assert find_canonical_name("Opaque White") == "White"
        assert find_canonical_name("UV Varnish") == "Varnish"
        assert find_canonical_name("NoVarnish") == "VarnishFree"

    @staticmethod
    def test_unknown_returns_none() -> None:
        assert find_canonical_name("Pantone 485 C") is None
        assert find_canonical_name("Custom_Brand_Spot") is None
        assert find_canonical_name("") is None


class TestCheckSpotNaming:
    @staticmethod
    def test_canonical_silent() -> None:
        pdf_bytes = _build_pdf_with_spots("CutContour")
        findings = check_spot_naming(pdf_bytes)
        assert findings == []

    @staticmethod
    def test_variant_fires_advisory() -> None:
        pdf_bytes = _build_pdf_with_spots("Cut Line")
        findings = check_spot_naming(pdf_bytes)
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_SPOT_NONCANONICAL"
        assert f.severity == Severity.ADVISORY
        assert f.details["actual_name"] == "Cut Line"
        assert f.details["canonical_name"] == "CutContour"

    @staticmethod
    def test_unknown_silent() -> None:
        """Pantone / brand names not in the taxonomy → silent."""
        pdf_bytes = _build_pdf_with_spots("Pantone 485 C")
        findings = check_spot_naming(pdf_bytes)
        assert findings == []

    @staticmethod
    def test_multiple_variants_fire_each() -> None:
        pdf_bytes = _build_pdf_with_spots("Cut Line", "FoldLine", "Perf")
        findings = check_spot_naming(pdf_bytes)
        canonicals = {f.details["canonical_name"] for f in findings}
        assert canonicals == {"CutContour", "Crease", "Perforation"}

    @staticmethod
    def test_canonical_names_set() -> None:
        """Sanity: the public CANONICAL_NAMES set contains the
        documented canonical names."""
        for n in (
            "CutContour",
            "Perforation",
            "Crease",
            "KissCut",
            "ThroughCut",
            "White",
            "Varnish",
            "VarnishFree",
        ):
            assert n in CANONICAL_NAMES

    @staticmethod
    def test_empty_pdf_silent() -> None:
        assert check_spot_naming(b"") == []
        assert check_spot_naming(b"not-a-pdf") == []
