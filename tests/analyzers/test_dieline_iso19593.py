"""Unit tests for ``LPDF_DIE_PROCESSING_STEPS`` (ISO 19593-1)."""

from __future__ import annotations

from lintpdf.analyzers.dieline_iso19593 import DielineIso19593Analyzer
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(spot_names: list[str]) -> SemanticDocument:
    """Build a doc whose page declares one Separation per spot name."""
    color_spaces = {}
    for i, name in enumerate(spot_names):
        cs = PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
        color_spaces[f"CS{i}"] = cs
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                color_spaces=color_spaces,
            )
        ],
    )


def test_single_dieline_no_iso_steps_fires() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["Dieline"]), events=[])
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_DIE_PROCESSING_STEPS"


def test_cutcontour_alone_fires() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["CutContour"]), events=[])
    assert len(findings) == 1


def test_dieline_plus_cutting_does_not_fire() -> None:
    """ISO 19593-1 decomposition present alongside generic dieline →
    converter has the routing info; don't double-flag."""
    findings = DielineIso19593Analyzer().analyze(_doc(["Dieline", "Cutting", "Crease"]), events=[])
    assert findings == []


def test_iso_steps_only_does_not_fire() -> None:
    """When the artwork uses canonical ISO names directly, no advisory."""
    findings = DielineIso19593Analyzer().analyze(
        _doc(["Cutting", "Crease", "Perforating"]), events=[]
    )
    assert findings == []


def test_no_dielines_does_not_fire() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["PMS185"]), events=[])
    assert findings == []


def test_case_insensitive_match() -> None:
    """``DIELINE`` (uppercase), ``Die-Line``, ``die_line`` all match."""
    for name in ("DIELINE", "Die-Line", "die_line", "Die Line"):
        findings = DielineIso19593Analyzer().analyze(_doc([name]), events=[])
        assert len(findings) == 1, name


def test_kiss_cut_recognized_as_iso_step() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["Dieline", "Kiss-Cut"]), events=[])
    assert findings == []


def test_foldline_recognized_as_iso_step() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["CutContour", "FoldLine"]), events=[])
    assert findings == []


def test_message_includes_original_spot_name() -> None:
    findings = DielineIso19593Analyzer().analyze(_doc(["CutContour"]), events=[])
    assert "CutContour" in findings[0].message or "cutcontour" in findings[0].message.lower()
