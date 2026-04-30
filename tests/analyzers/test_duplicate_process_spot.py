"""Unit tests for ``LPDF_SPOT_DUPE_PROCESS`` (process-as-spot detector)."""

from __future__ import annotations

from lintpdf.analyzers.duplicate_process_spot import DuplicateProcessSpotAnalyzer
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(color_spaces: dict[str, PdfColorSpace]) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces,
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def test_separation_named_cyan_fires() -> None:
    cs = PdfColorSpace(
        name="CS1",
        cs_type="Separation",
        components=1,
        colorant_names=("Cyan",),
    )
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"CS1": cs}), events=[])
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_SPOT_DUPE_PROCESS"
    assert findings[0].details["colorant"] == "Cyan"


def test_separation_process_cyan_fires() -> None:
    cs = PdfColorSpace(
        name="CS1",
        cs_type="Separation",
        components=1,
        colorant_names=("Process Cyan",),
    )
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"CS1": cs}), events=[])
    assert len(findings) == 1
    assert findings[0].details["colorant"] == "Process Cyan"


def test_devicen_with_process_channels_fires_each() -> None:
    """A DeviceN that mixes legit spots + process channels emits one
    finding per duplicated process channel (deduped globally)."""
    cs = PdfColorSpace(
        name="CS_DN",
        cs_type="DeviceN",
        components=4,
        colorant_names=("Cyan", "Magenta", "Yellow", "PMS185"),
    )
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"CS_DN": cs}), events=[])
    colorants = {f.details["colorant"] for f in findings}
    assert colorants == {"Cyan", "Magenta", "Yellow"}


def test_legit_spot_does_not_fire() -> None:
    cs = PdfColorSpace(
        name="CS1",
        cs_type="Separation",
        components=1,
        colorant_names=("PMS185",),
    )
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"CS1": cs}), events=[])
    assert findings == []


def test_devicergb_does_not_fire() -> None:
    """Standard process color spaces are NOT flagged — the rule only
    applies to Separation/DeviceN with a process-channel colorant
    name."""
    cs = PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4)
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"DeviceCMYK": cs}), events=[])
    assert findings == []


def test_dedupe_across_pages() -> None:
    """If two pages each declare a Separation 'Cyan', emit one
    finding (one duplicate plate is one duplicate plate)."""
    cs = PdfColorSpace(
        name="CS1",
        cs_type="Separation",
        components=1,
        colorant_names=("Cyan",),
    )
    page1 = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={"CS1": cs},
    )
    page2 = SemanticPage(
        page_num=2,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces={"CS1": cs},
    )
    doc = SemanticDocument(
        version="1.7",
        page_count=2,
        is_encrypted=False,
        pages=[page1, page2],
    )
    findings = DuplicateProcessSpotAnalyzer().analyze(doc, events=[])
    assert len(findings) == 1


def test_pattern_color_space_skipped() -> None:
    cs = PdfColorSpace(name="P1", cs_type="Pattern", components=0)
    findings = DuplicateProcessSpotAnalyzer().analyze(_doc({"P1": cs}), events=[])
    assert findings == []
