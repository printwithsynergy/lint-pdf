"""PR-U tests — metadata audit checks."""

from __future__ import annotations

from siftpdf.analyzers.metadata_audit import MetadataAuditAnalyzer
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(*, version: str = "1.7", spots: list[str] | None = None) -> SemanticDocument:
    color_spaces: dict[str, PdfColorSpace] = {}
    for i, name in enumerate(spots or []):
        color_spaces[f"CS{i}"] = PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces,
    )
    return SemanticDocument(version=version, page_count=1, is_encrypted=False, pages=[page])


# ── LPDF_DOC_PDF_VERSION_DATED ────────────────────────────────────


def test_pdf_version_1_3_fires() -> None:
    findings = MetadataAuditAnalyzer().analyze(_doc(version="1.3"), [])
    f = [x for x in findings if x.inspection_id == "LPDF_DOC_PDF_VERSION_DATED"]
    assert len(f) == 1
    assert f[0].details["pdf_version"] == "1.3"


def test_pdf_version_1_2_fires() -> None:
    findings = MetadataAuditAnalyzer().analyze(_doc(version="1.2"), [])
    assert any(x.inspection_id == "LPDF_DOC_PDF_VERSION_DATED" for x in findings)


def test_pdf_version_1_4_no_finding() -> None:
    findings = MetadataAuditAnalyzer().analyze(_doc(version="1.4"), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_DOC_PDF_VERSION_DATED"]


def test_pdf_version_1_7_no_finding() -> None:
    findings = MetadataAuditAnalyzer().analyze(_doc(version="1.7"), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_DOC_PDF_VERSION_DATED"]


def test_pdf_version_2_0_no_finding() -> None:
    findings = MetadataAuditAnalyzer().analyze(_doc(version="2.0"), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_DOC_PDF_VERSION_DATED"]


# ── LPDF_SPOT_NAME_CASE_MIXED ─────────────────────────────────────


def test_amalgam_buff_vs_beige_fires() -> None:
    """Amalgam_Catalyst case: /BUFF (UPPERCASE) alongside mixed-case
    /Lt Beige, /Med Beige, /Dark Biege, /Faint Beige."""
    findings = MetadataAuditAnalyzer().analyze(
        _doc(spots=["BUFF", "Lt Beige", "Med Beige", "Faint Beige"]), []
    )
    f = [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]
    assert len(f) == 1
    assert "BUFF" in f[0].details["uppercase_names"]
    assert "Lt Beige" in f[0].details["mixed_case_names"]


def test_uniform_uppercase_no_finding() -> None:
    """All-uppercase brand convention is internally consistent."""
    findings = MetadataAuditAnalyzer().analyze(
        _doc(spots=["BUFF", "FAINT BEIGE", "DARK BEIGE"]), []
    )
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]


def test_uniform_mixed_case_no_finding() -> None:
    """All mixed-case is internally consistent."""
    findings = MetadataAuditAnalyzer().analyze(
        _doc(spots=["Lt Beige", "Med Beige", "Dark Beige"]), []
    )
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]


def test_pantone_uppercase_does_not_trigger() -> None:
    """PANTONE prefix is library convention, shouldn't count toward
    case-mix conflict against mixed-case custom spots."""
    findings = MetadataAuditAnalyzer().analyze(_doc(spots=["PANTONE 185 C", "Brand Cream"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]


def test_process_and_dieline_excluded() -> None:
    """/Cyan, /Dieline, /Cutting are conventional and excluded."""
    findings = MetadataAuditAnalyzer().analyze(
        _doc(spots=["Cyan", "Dieline", "Cutting", "Lt Beige"]), []
    )
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]


def test_single_spot_no_finding() -> None:
    """Need at least 2 distinct custom spots to compare case."""
    findings = MetadataAuditAnalyzer().analyze(_doc(spots=["BUFF"]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_CASE_MIXED"]
