"""Tests for ``LPDF_TEXT_OUTLINED_SMALL`` — outlined-text legibility
fallback added in PR C Slot 3B.

The event-based ``LPDF_LEGIBILITY_001`` rule only sees live
``TextRenderedEvent``s. On stick-pack / pouch fixtures the ingredient
panel is converted to vector paths and never emits text events. The
fallback walks ``page.detected_text_regions`` (populated by PR #295's
shared OCR pass) and emits an ADVISORY when bbox heights measure below
6 pt.
"""

from __future__ import annotations

from lintpdf.analyzers.legibility_composite import LegibilityCompositeAnalyzer
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _doc_with_regions(*regions: DetectedTextRegion) -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
    page.detected_text_regions = list(regions) if regions else None
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


class TestOutlinedSmallText:
    @staticmethod
    def test_no_regions_no_finding() -> None:
        # Pass not run / GPU offline → no detected_text_regions → no finding.
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        )
        findings = LegibilityCompositeAnalyzer().analyze(doc, [])
        assert not [f for f in findings if f.inspection_id == "LPDF_TEXT_OUTLINED_SMALL"]

    @staticmethod
    def test_all_regions_above_threshold_no_finding() -> None:
        # Every region is >=6 pt tall — clean.
        doc = _doc_with_regions(
            DetectedTextRegion(bbox=PdfBox(100, 100, 300, 110), text="Big"),
            DetectedTextRegion(bbox=PdfBox(100, 200, 300, 215), text="Bigger"),
        )
        findings = LegibilityCompositeAnalyzer().analyze(doc, [])
        assert not [f for f in findings if f.inspection_id == "LPDF_TEXT_OUTLINED_SMALL"]

    @staticmethod
    def test_region_below_6pt_fires_advisory() -> None:
        # 4-pt-high outlined region (e.g. ingredient panel on a stick-pack).
        doc = _doc_with_regions(
            DetectedTextRegion(
                bbox=PdfBox(100, 100, 300, 104),  # height = 4pt
                text="Sucralose (sweetener), Citric Acid",
            )
        )
        findings = [
            f
            for f in LegibilityCompositeAnalyzer().analyze(doc, [])
            if f.inspection_id == "LPDF_TEXT_OUTLINED_SMALL"
        ]
        assert len(findings) == 1
        f = findings[0]
        assert f.severity.value == "advisory"
        assert "outlined text" in f.message.lower()
        # Per-region finding carries the individual height and bbox.
        assert f.details["apparent_height_pt"] == 4.0
        assert f.bbox == (100.0, 100.0, 300.0, 104.0)

    @staticmethod
    def test_one_finding_per_region_with_multiple_below() -> None:
        # 3 small regions on one page → 3 findings (one per region, capped at 5).
        doc = _doc_with_regions(
            DetectedTextRegion(bbox=PdfBox(0, 0, 100, 4), text="a"),
            DetectedTextRegion(bbox=PdfBox(0, 100, 100, 105), text="b"),
            DetectedTextRegion(bbox=PdfBox(0, 200, 100, 203), text="c"),
        )
        findings = [
            f
            for f in LegibilityCompositeAnalyzer().analyze(doc, [])
            if f.inspection_id == "LPDF_TEXT_OUTLINED_SMALL"
        ]
        assert len(findings) == 3
        # Each finding must carry a distinct bbox.
        bboxes = [f.bbox for f in findings]
        assert len(set(bboxes)) == 3
        heights = sorted(f.details["apparent_height_pt"] for f in findings)
        assert heights == [3.0, 4.0, 5.0]

    @staticmethod
    def test_sub_pixel_height_skipped_as_noise() -> None:
        # Heights below 1pt are scanner noise, not glyphs.
        doc = _doc_with_regions(DetectedTextRegion(bbox=PdfBox(0, 0, 100, 0.5), text="speck"))
        findings = [
            f
            for f in LegibilityCompositeAnalyzer().analyze(doc, [])
            if f.inspection_id == "LPDF_TEXT_OUTLINED_SMALL"
        ]
        assert findings == []
