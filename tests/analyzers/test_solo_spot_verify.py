"""PR-CC tests — single-spot-as-decoration verification."""

from __future__ import annotations

from siftpdf.analyzers.solo_spot_verify import SoloSpotVerifyAnalyzer
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(spots: list[str]) -> SemanticDocument:
    color_spaces = {
        f"CS{i}": PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
        for i, name in enumerate(spots)
    }
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def test_single_decorative_spot_fires() -> None:
    """Pavette case — single /rose pink Separation, non-dieline name."""
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["rose pink"]), [])
    f = [x for x in findings if x.inspection_id == "LPDF_SPOT_SOLO_VERIFY"]
    assert len(f) == 1
    assert f[0].details["colorant_name"] == "rose pink"


def test_single_dieline_spot_no_finding() -> None:
    """Single /Cutting Separation is clearly a technical layer — skip."""
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["Cutting"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_SOLO_VERIFY"]


def test_single_perforating_spot_no_finding() -> None:
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["Perforating"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_SOLO_VERIFY"]


def test_two_spots_no_finding() -> None:
    """Multi-spot inventory falls outside this rule's scope."""
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["PANTONE 211 C", "PANTONE 7401 C"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_SOLO_VERIFY"]


def test_no_spots_no_finding() -> None:
    findings = SoloSpotVerifyAnalyzer().analyze(_doc([]), [])
    assert not findings


def test_pantone_brand_spot_fires() -> None:
    """Single PANTONE spot with no dieline tokens still triggers the
    verification advisory."""
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["PANTONE 185 C"]), [])
    assert any(x.inspection_id == "LPDF_SPOT_SOLO_VERIFY" for x in findings)


def test_compound_dieline_token_suppressed() -> None:
    """`die_cut_outer` contains a dieline token — should suppress."""
    findings = SoloSpotVerifyAnalyzer().analyze(_doc(["die_cut_outer"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_SOLO_VERIFY"]
