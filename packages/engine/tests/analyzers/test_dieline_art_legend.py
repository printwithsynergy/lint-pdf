"""Unit tests for WS-D dieline / art-size / legend analyzers.

These exercise the deterministic pieces (name heuristic, bbox
math, position classifier). The Sonnet fallbacks are covered
separately by integration tests since they need a live API key.
"""

from __future__ import annotations

from typing import ClassVar

from lintpdf.analyzers.art_size import ArtSizeMM, compute_art_size
from lintpdf.analyzers.dieline import _name_matches
from lintpdf.analyzers.legend import classify_swatches


class _D:
    def __init__(self, **kw) -> None:
        self.source = kw.get("source", "missing")
        self.polylines = kw.get("polylines", [])
        self.spot_name = kw.get("spot_name")
        self.confidence = kw.get("confidence", 0.0)


class TestNameMatches:
    @staticmethod
    def test_cutcontour_matches_case_insensitively() -> None:
        assert _name_matches("CutContour") is True
        assert _name_matches("CUTCONTOUR") is True
        assert _name_matches("cutcontour") is True

    @staticmethod
    def test_dieline_variants_all_match() -> None:
        assert _name_matches("Dieline") is True
        assert _name_matches("Die-Line") is True
        assert _name_matches("Die Line") is True

    @staticmethod
    def test_crease_perf_kiss_match() -> None:
        for token in ("Crease", "Perf", "Perforation", "Kiss", "Score"):
            assert _name_matches(token) is True, token

    @staticmethod
    def test_cyan_does_not_match() -> None:
        assert _name_matches("Cyan") is False
        assert _name_matches("PANTONE 185 C") is False

    @staticmethod
    def test_embedded_match_still_hits() -> None:
        assert _name_matches("Brand_CutContour_layer") is True


class TestArtSize:
    @staticmethod
    def test_missing_dieline_returns_none() -> None:
        assert compute_art_size(None) is None
        assert compute_art_size(_D(source="missing")) is None

    @staticmethod
    def test_simple_rectangle() -> None:
        # 144pt x 72pt rectangle = 50.8mm x 25.4mm (before inset).
        d = _D(
            source="name",
            polylines=[
                [[0.0, 0.0], [144.0, 0.0], [144.0, 72.0], [0.0, 72.0], [0.0, 0.0]]
            ],
        )
        size = compute_art_size(d, stroke_pts=0.0)
        assert size == ArtSizeMM(width_mm=50.8, height_mm=25.4)

    @staticmethod
    def test_stroke_inset_reduces_centerline_size() -> None:
        d = _D(
            source="name",
            polylines=[
                [[0.0, 0.0], [144.0, 0.0], [144.0, 72.0], [0.0, 72.0]]
            ],
        )
        size = compute_art_size(d, stroke_pts=2.0)
        # Inset by 1pt on each side → 142pt x 70pt.
        assert size is not None
        assert round(size.width_mm, 2) == round(142 * 25.4 / 72.0, 2)
        assert round(size.height_mm, 2) == round(70 * 25.4 / 72.0, 2)

    @staticmethod
    def test_empty_polylines_returns_none() -> None:
        d = _D(source="name", polylines=[])
        assert compute_art_size(d) is None


class TestClassifySwatches:
    _OUTER: ClassVar[list[list[list[float]]]] = [
        [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0], [0.0, 0.0]]
    ]

    @staticmethod
    def test_swatch_outside_dieline_is_legend() -> None:
        out = classify_swatches(
            [{"spot_name": "Cyan", "bbox": [120.0, 120.0, 130.0, 130.0]}],
            _D(source="name", polylines=TestClassifySwatches._OUTER),
        )
        assert len(out) == 1
        assert out[0].kind == "legend"
        assert out[0].source == "position"

    @staticmethod
    def test_swatch_inside_dieline_is_art() -> None:
        out = classify_swatches(
            [{"spot_name": "Magenta", "bbox": [10.0, 10.0, 20.0, 20.0]}],
            _D(source="name", polylines=TestClassifySwatches._OUTER),
        )
        assert out[0].kind == "art"

    @staticmethod
    def test_swatch_straddling_is_unknown_without_sonnet() -> None:
        out = classify_swatches(
            [{"spot_name": "Spot", "bbox": [90.0, 90.0, 110.0, 110.0]}],
            _D(source="name", polylines=TestClassifySwatches._OUTER),
            ai_features=frozenset(),  # no sonnet_fallback grant
        )
        assert out[0].kind == "unknown"
        assert out[0].source == "position_only"

    @staticmethod
    def test_missing_dieline_marks_all_unknown() -> None:
        out = classify_swatches(
            [{"spot_name": "X", "bbox": [0, 0, 10, 10]}],
            _D(source="missing"),
            ai_features=frozenset(),
        )
        assert out[0].kind == "unknown"
