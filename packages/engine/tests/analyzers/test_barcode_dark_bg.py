"""PR-Z tests — barcode on tinted / coloured background."""

from __future__ import annotations

from lintpdf.analyzers.barcode import BarcodeAnalyzer, _BarcodeCandidate
from lintpdf.semantic.events import PathPaintingEvent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc() -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _candidate(
    bbox: tuple[float, float, float, float] = (100, 100, 200, 200),
    narrow_bar: float = 0.5,
) -> _BarcodeCandidate:
    c = _BarcodeCandidate(page_num=1)
    x0, y0, x1, y1 = bbox
    c.add_stroke(narrow_bar, bbox=(x0, y0, x0 + narrow_bar, y1))
    c.add_stroke(narrow_bar, bbox=(x1 - narrow_bar, y0, x1, y1))
    c.stroke_widths = [narrow_bar] * 30
    return c


def _fill(
    *,
    bbox: tuple[float, float, float, float],
    cs: str,
    vals: tuple[float, ...],
    page_num: int = 1,
    opi: int = 0,
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=opi,
        fill=True,
        stroke=False,
        fill_color_space=cs,
        fill_color_values=vals,
        bbox=bbox,
    )


# ── Tinted backgrounds fire ───────────────────────────────────────────


def test_pantone_spot_fill_overlapping_quiet_zone_fires() -> None:
    """Pink Pantone fill in the quiet zone with no white knockout fires."""
    doc = _doc()
    c = _candidate()
    fills = [
        _fill(
            bbox=(80, 80, 220, 220),  # encloses the QZ halo (5pt)
            cs="Separation Pantone 211 C",
            vals=(1.0,),
        ),
    ]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert len(findings) == 1
    f = findings[0]
    assert f.inspection_id == "LPDF_BARCODE_DARK_BG"
    assert f.severity.value == "warning"
    assert f.details["tinted_fill_count"] == 1


def test_dark_cmyk_fill_fires() -> None:
    """30% C + 40% M + 30% Y = 100% total > 10% threshold → tinted."""
    doc = _doc()
    c = _candidate()
    fills = [_fill(bbox=(80, 80, 220, 220), cs="DeviceCMYK", vals=(0.3, 0.4, 0.3, 0.0))]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert any(f.inspection_id == "LPDF_BARCODE_DARK_BG" for f in findings)


def test_grey_fill_below_white_threshold_fires() -> None:
    """DeviceGray 0.6 → not white; counts as tinted."""
    doc = _doc()
    c = _candidate()
    fills = [_fill(bbox=(80, 80, 220, 220), cs="DeviceGray", vals=(0.6,))]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert any(f.inspection_id == "LPDF_BARCODE_DARK_BG" for f in findings)


# ── White knockout suppresses ─────────────────────────────────────────


def test_white_cmyk_knockout_box_suppresses() -> None:
    """A CMYK 0,0,0,0 fill that fully encloses the barcode bbox is the
    classic knockout box. Tinted fill outside it doesn't count because
    the box covers the bars."""
    doc = _doc()
    c = _candidate()
    fills = [
        _fill(
            bbox=(80, 80, 220, 220),
            cs="Separation Pantone 211 C",
            vals=(1.0,),
            opi=0,
        ),
        _fill(
            bbox=(95, 95, 205, 205),  # white box covering barcode
            cs="DeviceCMYK",
            vals=(0.0, 0.0, 0.0, 0.0),
            opi=1,
        ),
    ]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert findings == []


def test_white_rgb_knockout_box_suppresses() -> None:
    doc = _doc()
    c = _candidate()
    fills = [
        _fill(bbox=(80, 80, 220, 220), cs="DeviceCMYK", vals=(0.5, 0.0, 0.0, 0.0)),
        _fill(bbox=(95, 95, 205, 205), cs="DeviceRGB", vals=(1.0, 1.0, 1.0)),
    ]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert findings == []


# ── No tinted fill: silent ────────────────────────────────────────────


def test_no_fills_no_finding() -> None:
    doc = _doc()
    c = _candidate()
    assert BarcodeAnalyzer()._check_barcode_background([c], doc, []) == []


def test_white_only_fills_no_finding() -> None:
    """Only white fills around the barcode (background page, knockout
    box). Nothing tinted to flag."""
    doc = _doc()
    c = _candidate()
    fills = [_fill(bbox=(0, 0, 612, 792), cs="DeviceCMYK", vals=(0.0, 0.0, 0.0, 0.0))]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert findings == []


def test_far_away_tinted_fill_no_finding() -> None:
    """Tinted fill clearly outside the quiet zone halo — no overlap."""
    doc = _doc()
    c = _candidate()
    fills = [_fill(bbox=(300, 300, 400, 400), cs="DeviceCMYK", vals=(0.5, 0.5, 0.0, 0.0))]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert findings == []


def test_zero_tint_separation_treated_as_light() -> None:
    """A Separation spot at 0% tint puts no ink down — treat it as
    transparent / light, so it doesn't trip the check."""
    doc = _doc()
    c = _candidate()
    fills = [_fill(bbox=(80, 80, 220, 220), cs="Separation Pantone 485 C", vals=(0.0,))]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert findings == []


# ── Dedupe: one finding per barcode ───────────────────────────────────


def test_one_finding_per_barcode_with_many_tinted_fills() -> None:
    doc = _doc()
    c = _candidate()
    fills = [
        _fill(bbox=(80, 80, 220, 220), cs="DeviceCMYK", vals=(0.2, 0.3, 0.0, 0.0), opi=i)
        for i in range(6)
    ]
    findings = BarcodeAnalyzer()._check_barcode_background([c], doc, fills)
    assert len(findings) == 1
