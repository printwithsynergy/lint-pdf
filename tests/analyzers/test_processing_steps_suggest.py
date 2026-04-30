"""Tests for T2-ISO05 — LPDF_PSTEP_SUGGEST.

Uses pikepdf to construct synthetic PDFs with Separation / DeviceN
spot colours so the analyzer's pikepdf walker picks them up.
"""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.spot_name_normaliser import (
    ISO_19593_GROUP_BY_CANONICAL,
    suggest_processing_steps,
)


def _pdf_with_separation_spots(spot_names: list[str]) -> bytes:
    """Build a 1-page PDF whose page resources declare each name as
    a Separation colour space."""
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0]
    cs_dict = pikepdf.Dictionary()
    for idx, name in enumerate(spot_names, start=1):
        sep = pikepdf.Array(
            [
                pikepdf.Name("/Separation"),
                pikepdf.Name(f"/{name}"),
                pikepdf.Name("/DeviceCMYK"),
                pikepdf.Dictionary(
                    {
                        "/FunctionType": 2,
                        "/Domain": [0.0, 1.0],
                        "/Range": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
                        "/N": 1,
                        "/C0": [0.0, 0.0, 0.0, 0.0],
                        "/C1": [0.0, 0.0, 0.0, 1.0],
                    }
                ),
            ]
        )
        cs_dict[f"/CS{idx}"] = sep

    resources = pikepdf.Dictionary({"/ColorSpace": cs_dict})
    page.obj["/Resources"] = resources

    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


class TestProcessingStepsSuggest:
    @staticmethod
    def test_silent_on_empty_pdf() -> None:
        assert suggest_processing_steps(b"") == []

    @staticmethod
    def test_silent_on_no_spots() -> None:
        pdf_bytes = _pdf_with_separation_spots([])
        assert suggest_processing_steps(pdf_bytes) == []

    @staticmethod
    def test_cut_contour_suggests_cutting() -> None:
        pdf_bytes = _pdf_with_separation_spots(["CutContour"])
        out = suggest_processing_steps(pdf_bytes)
        assert len(out) == 1
        f = out[0]
        assert f.inspection_id == "LPDF_PSTEP_SUGGEST"
        assert f.details["iso_group"] == "Cutting"
        assert f.details["canonical_name"] == "CutContour"

    @staticmethod
    def test_kisscut_suggests_kisscutting() -> None:
        pdf_bytes = _pdf_with_separation_spots(["KissCut"])
        out = suggest_processing_steps(pdf_bytes)
        assert len(out) == 1
        assert out[0].details["iso_group"] == "KissCutting"

    @staticmethod
    def test_unknown_spot_silent() -> None:
        pdf_bytes = _pdf_with_separation_spots(["Pantone_185"])
        assert suggest_processing_steps(pdf_bytes) == []

    @staticmethod
    def test_multiple_spots_emit_one_each() -> None:
        pdf_bytes = _pdf_with_separation_spots(["CutContour", "Crease", "Varnish", "White"])
        out = suggest_processing_steps(pdf_bytes)
        groups = {f.details["iso_group"] for f in out}
        assert groups == {"Cutting", "Folding", "Varnish", "White"}

    @staticmethod
    def test_iso_mapping_table_complete() -> None:
        """Every canonical name should have an ISO mapping or be
        explicitly absent — a missing entry in the map silently
        omits suggestions."""
        from lintpdf.analyzers.spot_name_normaliser import CANONICAL_NAMES

        # Every canonical name in our taxonomy maps to an ISO group.
        for name in CANONICAL_NAMES:
            assert name in ISO_19593_GROUP_BY_CANONICAL, (
                f"Canonical name {name!r} has no ISO 19593-1 group mapping"
            )
