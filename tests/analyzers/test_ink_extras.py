"""Unit tests for ``InkExtrasAnalyzer`` — LPDF_INK_PRESS_STATIONS +
LPDF_INK_DUPLICATE_DEVICEN_SEP."""

from __future__ import annotations

from lintpdf.analyzers.ink_extras import InkExtrasAnalyzer
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(*color_spaces: PdfColorSpace) -> SemanticDocument:
    cs_dict = {f"CS{i}": cs for i, cs in enumerate(color_spaces)}
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                color_spaces=cs_dict,
            )
        ],
    )


def _sep(name: str) -> PdfColorSpace:
    return PdfColorSpace(
        name=name,
        cs_type="Separation",
        components=1,
        colorant_names=(name,),
    )


def _devicen(*colorants: str) -> PdfColorSpace:
    return PdfColorSpace(
        name="DN",
        cs_type="DeviceN",
        components=len(colorants),
        colorant_names=tuple(colorants),
    )


def _cmyk() -> PdfColorSpace:
    return PdfColorSpace(name="CMYK", cs_type="DeviceCMYK", components=4)


# -- LPDF_INK_PRESS_STATIONS ------------------------------------------------


def test_press_stations_six_or_under_no_flag() -> None:
    """4 process + 2 spots = 6 channels — at the limit, no flag."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(_cmyk(), _sep("PANTONE 185 C"), _sep("PANTONE 286 C")), events=[]
    )
    psf = [f for f in findings if f.inspection_id == "LPDF_INK_PRESS_STATIONS"]
    assert psf == []


def test_press_stations_seven_fires_advisory() -> None:
    """4 process + 3 spots = 7 channels — fires."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(
            _cmyk(),
            _sep("PANTONE 185 C"),
            _sep("PANTONE 286 C"),
            _sep("PANTONE 7401 C"),
        ),
        events=[],
    )
    psf = [f for f in findings if f.inspection_id == "LPDF_INK_PRESS_STATIONS"]
    assert len(psf) == 1
    assert psf[0].details["total_printable"] == 7
    assert psf[0].severity.value == "advisory"


def test_press_stations_excludes_dieline() -> None:
    """Dieline / cut / perf don't count toward press capacity."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(
            _cmyk(),
            _sep("PANTONE 185 C"),
            _sep("PANTONE 286 C"),
            _sep("Dieline"),
            _sep("Perforating"),
            _sep("Varnish"),
        ),
        events=[],
    )
    psf = [f for f in findings if f.inspection_id == "LPDF_INK_PRESS_STATIONS"]
    # 4 process + 2 spots = 6 → no flag despite 3 technical specs.
    assert psf == []


def test_press_stations_seven_spots_no_process() -> None:
    """7 spot-only inks (no process) still fires."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(*[_sep(f"PANTONE {n} C") for n in (185, 286, 7401, 199, 200, 201, 202)]),
        events=[],
    )
    psf = [f for f in findings if f.inspection_id == "LPDF_INK_PRESS_STATIONS"]
    assert len(psf) == 1
    assert psf[0].details["total_printable"] == 7


def test_press_stations_custom_limit() -> None:
    """Allow tightening the limit (e.g. for narrow-web)."""
    findings = InkExtrasAnalyzer(station_limit=4).analyze(
        _doc(_cmyk(), _sep("PANTONE 185 C")), events=[]
    )
    psf = [f for f in findings if f.inspection_id == "LPDF_INK_PRESS_STATIONS"]
    assert len(psf) == 1


# -- LPDF_INK_DUPLICATE_DEVICEN_SEP -----------------------------------------


def test_devicen_sep_duplicate_fires() -> None:
    """Pink-Slush case: PANTONE 237 C in both Separation and DeviceN."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(
            _sep("PANTONE 237 C"),
            _devicen("C", "M", "Y", "K", "PANTONE 237 C"),
        ),
        events=[],
    )
    dup = [f for f in findings if f.inspection_id == "LPDF_INK_DUPLICATE_DEVICEN_SEP"]
    assert len(dup) == 1
    assert dup[0].details["colorant"] == "PANTONE 237 C"
    assert "DeviceN" in dup[0].details["cs_types"]
    assert "Separation" in dup[0].details["cs_types"]
    assert dup[0].severity.value == "warning"


def test_devicen_only_no_flag() -> None:
    """A colorant inside DeviceN with no separate Separation cs is fine."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(_devicen("C", "M", "Y", "K", "PANTONE 237 C")),
        events=[],
    )
    dup = [f for f in findings if f.inspection_id == "LPDF_INK_DUPLICATE_DEVICEN_SEP"]
    assert dup == []


def test_separation_only_no_flag() -> None:
    """Standalone Separation cs is fine."""
    findings = InkExtrasAnalyzer().analyze(_doc(_sep("PANTONE 237 C")), events=[])
    dup = [f for f in findings if f.inspection_id == "LPDF_INK_DUPLICATE_DEVICEN_SEP"]
    assert dup == []


def test_two_devicen_no_flag() -> None:
    """Same name in two DeviceN tuples (no Separation) doesn't fire — that's
    a different problem (and Acrobat collapses them at the RIP)."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(
            _devicen("C", "M", "Y", "K", "PANTONE 237 C"),
            _devicen("PANTONE 237 C", "PANTONE 286 C"),
        ),
        events=[],
    )
    dup = [f for f in findings if f.inspection_id == "LPDF_INK_DUPLICATE_DEVICEN_SEP"]
    assert dup == []


def test_multiple_dupe_pantones_emit_separately() -> None:
    """Pink-Slush real case: two Pantones each duplicated."""
    findings = InkExtrasAnalyzer().analyze(
        _doc(
            _sep("PANTONE 236 C"),
            _sep("PANTONE 237 C"),
            _devicen("C", "M", "Y", "K", "PANTONE 236 C", "PANTONE 237 C"),
        ),
        events=[],
    )
    dup = [f for f in findings if f.inspection_id == "LPDF_INK_DUPLICATE_DEVICEN_SEP"]
    assert len(dup) == 2
    colorants = {f.details["colorant"] for f in dup}
    assert colorants == {"PANTONE 236 C", "PANTONE 237 C"}


def test_clean_doc_emits_nothing() -> None:
    findings = InkExtrasAnalyzer().analyze(_doc(_cmyk(), _sep("PANTONE 185 C")), events=[])
    assert findings == []
