"""Tests for PrepressAnalyzer — GRD_PRESS_001-003."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.analyzers.prepress import PrepressAnalyzer
from grounded.semantic.events import PrepressStateChangedEvent
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestHalftoneDetection:
    """Test GRD_PRESS_001: custom halftone dictionary."""

    @staticmethod
    def test_halftone_advisory() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_halftone=True,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        ht = [f for f in findings if f.inspection_id == "GRD_PRESS_001"]
        assert len(ht) == 1
        assert ht[0].severity == Severity.ADVISORY
        assert ht[0].page_num == 1

    @staticmethod
    def test_no_halftone_no_finding() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_halftone=False,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        ht = [f for f in findings if f.inspection_id == "GRD_PRESS_001"]
        assert len(ht) == 0

    @staticmethod
    def test_halftone_deduplication() -> None:
        """Multiple halftone events produce only one finding."""
        events = [
            PrepressStateChangedEvent(
                operator="gs", page_num=1, operator_index=0, has_halftone=True
            ),
            PrepressStateChangedEvent(
                operator="gs", page_num=1, operator_index=5, has_halftone=True
            ),
        ]
        findings = PrepressAnalyzer().analyze(_make_document(), events)
        ht = [f for f in findings if f.inspection_id == "GRD_PRESS_001"]
        assert len(ht) == 1


class TestTransferFunction:
    """Test GRD_PRESS_002: transfer function detection."""

    @staticmethod
    def test_transfer_function_delay() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_transfer_function=True,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        tf = [f for f in findings if f.inspection_id == "GRD_PRESS_002"]
        assert len(tf) == 1
        assert tf[0].severity == Severity.WARNING

    @staticmethod
    def test_no_transfer_no_finding() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_transfer_function=False,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        tf = [f for f in findings if f.inspection_id == "GRD_PRESS_002"]
        assert len(tf) == 0

    @staticmethod
    def test_transfer_deduplication() -> None:
        """Multiple transfer events produce only one finding."""
        events = [
            PrepressStateChangedEvent(
                operator="gs", page_num=1, operator_index=0, has_transfer_function=True
            ),
            PrepressStateChangedEvent(
                operator="gs", page_num=2, operator_index=0, has_transfer_function=True
            ),
        ]
        findings = PrepressAnalyzer().analyze(_make_document(), events)
        tf = [f for f in findings if f.inspection_id == "GRD_PRESS_002"]
        assert len(tf) == 1


class TestBGUCR:
    """Test GRD_PRESS_003: custom BG/UCR function."""

    @staticmethod
    def test_bg_ucr_advisory() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_bg_ucr=True,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        bg = [f for f in findings if f.inspection_id == "GRD_PRESS_003"]
        assert len(bg) == 1
        assert bg[0].severity == Severity.ADVISORY

    @staticmethod
    def test_no_bg_ucr_no_finding() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_bg_ucr=False,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        bg = [f for f in findings if f.inspection_id == "GRD_PRESS_003"]
        assert len(bg) == 0

    @staticmethod
    def test_bg_ucr_deduplication() -> None:
        """Multiple BG/UCR events produce only one finding."""
        events = [
            PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=0, has_bg_ucr=True),
            PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=5, has_bg_ucr=True),
        ]
        findings = PrepressAnalyzer().analyze(_make_document(), events)
        bg = [f for f in findings if f.inspection_id == "GRD_PRESS_003"]
        assert len(bg) == 1


class TestCombinedPrepressEvents:
    """Test multiple prepress features in one event."""

    @staticmethod
    def test_all_features_in_one_event() -> None:
        """Event with halftone, transfer, and BG/UCR triggers all three."""
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_halftone=True,
            has_transfer_function=True,
            has_bg_ucr=True,
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        ids = {f.inspection_id for f in findings}
        assert "GRD_PRESS_001" in ids
        assert "GRD_PRESS_002" in ids
        assert "GRD_PRESS_003" in ids

    @staticmethod
    def test_no_prepress_events() -> None:
        """Empty events produce no findings."""
        findings = PrepressAnalyzer().analyze(_make_document(), [])
        press_findings = [f for f in findings if f.inspection_id.startswith("GRD_PRESS_")]
        assert len(press_findings) == 0

    @staticmethod
    def test_non_prepress_events_ignored() -> None:
        """Non-PrepressStateChangedEvent events are ignored."""
        from grounded.semantic.events import OpacityChangedEvent

        event = OpacityChangedEvent(
            operator="gs", page_num=1, operator_index=0, non_stroking_alpha=0.5
        )
        findings = PrepressAnalyzer().analyze(_make_document(), [event])
        press_findings = [f for f in findings if f.inspection_id.startswith("GRD_PRESS_")]
        assert len(press_findings) == 0
