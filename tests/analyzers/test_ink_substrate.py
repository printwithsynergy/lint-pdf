"""Tests for T3-D12 LPDF_INK_SUBSTRATE (substrate-aware TAC advisory)."""

from __future__ import annotations

import pytest

from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.ink_coverage_analyzer import (
    InkCoverageAnalyzer,
    get_substrate_tac_limit,
)
from siftpdf.semantic.events import (
    ContentStreamEvent,
    PathPaintingEvent,
)
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_cmyk_fill_event(
    c: float, m: float, y: float, k: float, page_num: int = 1
) -> PathPaintingEvent:
    """Synthesize a PathPaintingEvent with a CMYK fill colour and a
    non-trivial bbox so the analyzer records a TAC sample."""
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=1,
        fill=True,
        stroke=False,
        fill_color_space="DeviceCMYK",
        fill_color_values=(c, m, y, k),
        line_width=1.0,
        bbox=(100.0, 100.0, 200.0, 200.0),
    )


def _make_doc() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestSubstrateLookup:
    @staticmethod
    def test_known_substrates_map() -> None:
        assert get_substrate_tac_limit("uncoated_offset") == 280.0
        assert get_substrate_tac_limit("coated_offset") == 300.0
        assert get_substrate_tac_limit("newsprint") == 240.0
        assert get_substrate_tac_limit("digital") == 320.0
        assert get_substrate_tac_limit("flexo") == 260.0
        assert get_substrate_tac_limit("gravure") == 300.0
        assert get_substrate_tac_limit("large_format") == 280.0

    @staticmethod
    def test_case_insensitive() -> None:
        assert get_substrate_tac_limit("UNCOATED_OFFSET") == 280.0
        assert get_substrate_tac_limit("  Coated_Offset  ") == 300.0

    @staticmethod
    def test_unknown_returns_none() -> None:
        assert get_substrate_tac_limit("parchment") is None
        assert get_substrate_tac_limit(None) is None
        assert get_substrate_tac_limit("") is None


class TestNoSubstrate:
    @staticmethod
    def test_no_substrate_no_finding() -> None:
        """Default analyzer has no substrate → LPDF_INK_SUBSTRATE never fires."""
        analyzer = InkCoverageAnalyzer()
        doc = _make_doc()
        # Paint 350% TAC — would violate every substrate
        events: list[ContentStreamEvent] = [
            _make_cmyk_fill_event(1.0, 1.0, 1.0, 0.5),
        ]
        findings = analyzer.analyze(doc, events)
        substrate = [f for f in findings if f.inspection_id == "LPDF_INK_SUBSTRATE"]
        assert substrate == []


class TestSubstrateViolation:
    @staticmethod
    def test_uncoated_offset_violation_fires() -> None:
        """Substrate=uncoated_offset (280% limit), paint 310% → fires."""
        analyzer = InkCoverageAnalyzer(substrate="uncoated_offset")
        doc = _make_doc()
        events: list[ContentStreamEvent] = [
            _make_cmyk_fill_event(0.9, 0.9, 0.7, 0.6),  # 310%
        ]
        findings = analyzer.analyze(doc, events)
        substrate = [f for f in findings if f.inspection_id == "LPDF_INK_SUBSTRATE"]
        assert len(substrate) == 1
        f = substrate[0]
        assert f.severity == Severity.ADVISORY
        assert f.details["substrate"] == "uncoated_offset"
        assert f.details["substrate_tac_limit"] == 280.0
        assert f.details["observed_max_tac"] > 280.0

    @staticmethod
    def test_newsprint_violation_fires() -> None:
        """Newsprint limit is 240%. Paint 260% → fires."""
        analyzer = InkCoverageAnalyzer(substrate="newsprint")
        doc = _make_doc()
        events: list[ContentStreamEvent] = [
            _make_cmyk_fill_event(0.8, 0.8, 0.5, 0.5),  # 260%
        ]
        findings = analyzer.analyze(doc, events)
        substrate = [f for f in findings if f.inspection_id == "LPDF_INK_SUBSTRATE"]
        assert len(substrate) == 1
        assert substrate[0].details["substrate"] == "newsprint"
        assert substrate[0].details["substrate_tac_limit"] == 240.0


class TestSubstrateCompliant:
    @staticmethod
    def test_within_substrate_limit_silent() -> None:
        """Substrate=uncoated_offset (280%), paint 250% → no substrate
        advisory (compliant)."""
        analyzer = InkCoverageAnalyzer(substrate="uncoated_offset")
        doc = _make_doc()
        events: list[ContentStreamEvent] = [
            _make_cmyk_fill_event(0.8, 0.8, 0.5, 0.4),  # 250%
        ]
        findings = analyzer.analyze(doc, events)
        substrate = [f for f in findings if f.inspection_id == "LPDF_INK_SUBSTRATE"]
        assert substrate == []

    @staticmethod
    def test_unknown_substrate_silent() -> None:
        """Unknown substrate string → no lookup → no finding even on
        high TAC."""
        analyzer = InkCoverageAnalyzer(substrate="parchment")
        doc = _make_doc()
        events: list[ContentStreamEvent] = [
            _make_cmyk_fill_event(1.0, 1.0, 1.0, 0.5),
        ]
        findings = analyzer.analyze(doc, events)
        substrate = [f for f in findings if f.inspection_id == "LPDF_INK_SUBSTRATE"]
        assert substrate == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
