"""PR-AA tests — seal-zone keepout analyzer."""

from __future__ import annotations

from lintpdf.analyzers.seal_zone_keepout import SealZoneKeepoutAnalyzer
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _doc(
    detected_regions: list[DetectedTextRegion] | None = None,
    content_stream: bytes | None = None,
) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        detected_text_regions=tuple(detected_regions or ()),
        content_stream=content_stream or b"",
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _text(
    *,
    string: str,
    bbox: tuple[float, float, float, float],
    page_num: int = 1,
    operator_index: int = 0,
    rendering_mode: int = 0,
) -> TextRenderedEvent:
    identity = TransformationMatrix(1, 0, 0, 1, 0, 0)
    ev = TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=operator_index,
        font_name="F1",
        font_size=8.0,
        ctm=identity,
        text_matrix=identity,
        rendering_mode=rendering_mode,
        bbox=bbox,
    )
    # `string` is not a TextRenderedEvent dataclass field; attach it
    # separately so the analyzer's getattr() lookup finds it.
    object.__setattr__(ev, "string", string)
    return ev


# ── Live-text anchors ─────────────────────────────────────────────────


def test_live_copy_inside_keepout_fires() -> None:
    """Content stream contains an ``END SEAL`` label; live copy in the
    bottom 5 mm band of the MediaBox fires the keepout finding."""
    cs = b"BT /F1 8 Tf (END SEAL) Tj ET"
    # MediaBox is 0,0 to 612,792 — bottom 5 mm band is y in [0, 14.17].
    violator = _text(string="ingredients", bbox=(100.0, 5.0, 230.0, 12.0), operator_index=1)
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(content_stream=cs), [violator])
    seal = [f for f in findings if f.inspection_id == "LPDF_BOX_SEAL_ZONE_VIOLATION"]
    assert len(seal) >= 1
    assert "END SEAL" in seal[0].details["seal_label"]


def test_copy_far_from_seal_no_finding() -> None:
    """Live copy in the middle of the page (far from MediaBox edges) is
    well outside the synthesised top/bottom 5 mm keepout bands — no
    finding."""
    cs = b"BT /F1 8 Tf (END SEAL) Tj ET"
    far = _text(string="big body copy", bbox=(100.0, 400.0, 200.0, 420.0), operator_index=1)
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(content_stream=cs), [far])
    assert not [f for f in findings if f.inspection_id == "LPDF_BOX_SEAL_ZONE_VIOLATION"]


def test_no_seal_anchor_no_finding() -> None:
    """No seal label on the page → analyzer should return early."""
    cs = b"BT /F1 8 Tf (hello world) Tj ET"
    text = _text(string="hello", bbox=(100.0, 700.0, 200.0, 710.0))
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(content_stream=cs), [text])
    assert not findings


def test_overlap_in_seal_label() -> None:
    """`OVERLAP IN SEAL` content-stream label fires keepout for top-edge
    text events."""
    cs = b"BT /F1 8 Tf (OVERLAP IN SEAL) Tj ET"
    # MediaBox top is 792; 5 mm band is y in [777.83, 792].
    violator = _text(string="brand", bbox=(50.0, 785.0, 180.0, 791.0), operator_index=1)
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(content_stream=cs), [violator])
    assert any(f.inspection_id == "LPDF_BOX_SEAL_ZONE_VIOLATION" for f in findings)


def test_invisible_text_violator_skipped() -> None:
    """Invisible (rendering mode 3) text isn't a real violator."""
    cs = b"BT /F1 8 Tf (END SEAL) Tj ET"
    invisible = _text(
        string="hidden",
        bbox=(100.0, 5.0, 230.0, 12.0),
        operator_index=1,
        rendering_mode=3,
    )
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(content_stream=cs), [invisible])
    assert not [f for f in findings if f.inspection_id == "LPDF_BOX_SEAL_ZONE_VIOLATION"]


# ── OCR-region anchors ────────────────────────────────────────────────


def test_ocr_seal_label_anchors_keepout() -> None:
    """OCR-detected `TEAR ACROSS` region acts as the anchor."""
    region = DetectedTextRegion(
        bbox=PdfBox(100.0, 700.0, 180.0, 710.0),
        text="TEAR ACROSS / DÉCHIRER ICI",
    )
    violator = _text(string="copy", bbox=(170.0, 705.0, 220.0, 715.0))
    findings = SealZoneKeepoutAnalyzer().analyze(_doc(detected_regions=[region]), [violator])
    assert any(f.inspection_id == "LPDF_BOX_SEAL_ZONE_VIOLATION" for f in findings)
