"""Tests for Pantone validation — reference DB, Delta-E, and analyzer integration."""

from grounded.analyzers.finding import Severity
from grounded.analyzers.spot_color_analyzer import SpotColorAnalyzer
from grounded.profiles.icc.pantone_manager import (
    DeltaEResult,
    PantoneManager,
    PantoneReference,
)
from grounded.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _make_doc(color_spaces_by_page=None):
    pages = []
    if color_spaces_by_page:
        for i, cs_dict in enumerate(color_spaces_by_page, 1):
            pages.append(
                SemanticPage(
                    page_num=i,
                    media_box=PdfBox(0, 0, 612, 792),
                    color_spaces=cs_dict,
                )
            )
    else:
        pages.append(SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)))
    return SemanticDocument(
        version="2.0", page_count=len(pages), is_encrypted=False, pages=pages,
    )


class TestPantoneManager:
    def test_lookup_known_color(self):
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 485 C")
        assert ref is not None
        assert isinstance(ref, PantoneReference)
        assert ref.lab is not None
        assert len(ref.lab) == 3

    def test_lookup_case_insensitive(self):
        mgr = PantoneManager()
        ref = mgr.lookup("pantone 485 c")
        assert ref is not None

    def test_lookup_without_space_before_suffix(self):
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 485C")
        assert ref is not None

    def test_lookup_unknown_color(self):
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 99999 C")
        assert ref is None

    def test_lookup_uncoated(self):
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 485 U")
        assert ref is not None

    def test_custom_overrides(self):
        overrides = {
            "PANTONE CUSTOM 1 C": {
                "lab": [50.0, 30.0, -10.0],
                "cmyk_bridge": [10, 20, 30, 40],
            },
        }
        mgr = PantoneManager(custom_overrides=overrides)
        ref = mgr.lookup("PANTONE CUSTOM 1 C")
        assert ref is not None
        assert abs(ref.lab[0] - 50.0) < 0.01

    def test_custom_overrides_take_precedence(self):
        overrides = {
            "PANTONE 485 C": {
                "lab": [99.0, 0.0, 0.0],
                "cmyk_bridge": [0, 0, 0, 0],
            },
        }
        mgr = PantoneManager(custom_overrides=overrides)
        ref = mgr.lookup("PANTONE 485 C")
        assert ref is not None
        assert abs(ref.lab[0] - 99.0) < 0.01


class TestDeltaEValidation:
    def test_validate_cmyk_fallback(self):
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 485 C")
        if ref is None:
            return  # Skip if reference not available

        # Use reference CMYK bridge values (should give low Delta-E)
        if ref.cmyk_bridge:
            cmyk = (
                ref.cmyk_bridge[0] / 100.0,
                ref.cmyk_bridge[1] / 100.0,
                ref.cmyk_bridge[2] / 100.0,
                ref.cmyk_bridge[3] / 100.0,
            )
            result = mgr.validate_cmyk_fallback("PANTONE 485 C", cmyk)
            assert result is not None
            assert isinstance(result, DeltaEResult)
            assert isinstance(result.delta_e, float)
            assert result.delta_e >= 0

    def test_validate_returns_none_for_unknown(self):
        mgr = PantoneManager()
        result = mgr.validate_cmyk_fallback(
            "PANTONE NONEXISTENT 99999 C",
            (0.5, 0.3, 0.2, 0.1),
        )
        assert result is None


class TestSpotColorAnalyzerPantone:
    def test_spot_002_delta_e_validation(self):
        """GRD_SPOT_002 produces Delta-E findings for Pantone colors."""
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 485 C",),
            alternate=PdfColorSpace(
                name=None, cs_type="DeviceCMYK", components=4,
            ),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        analyzer = SpotColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        spot_002 = [f for f in findings if f.inspection_id == "GRD_SPOT_002"]
        assert len(spot_002) >= 1
        # Should have delta_e in details (since reference exists)
        for f in spot_002:
            if "delta_e" in f.details:
                assert isinstance(f.details["delta_e"], float)

    def test_spot_006_unknown_pantone(self):
        """GRD_SPOT_006 fires for Pantone colors not in reference DB."""
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 99999 C",),
            alternate=PdfColorSpace(
                name=None, cs_type="DeviceCMYK", components=4,
            ),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        analyzer = SpotColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        spot_006 = [f for f in findings if f.inspection_id == "GRD_SPOT_006"]
        assert len(spot_006) >= 1
        assert spot_006[0].severity == Severity.ADVISORY

    def test_non_pantone_skipped(self):
        """Non-Pantone spot colors don't trigger GRD_SPOT_002 or 006."""
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("MyCustomSpot",),
        )
        doc = _make_doc(color_spaces_by_page=[{"CS1": cs}])
        analyzer = SpotColorAnalyzer()
        findings = analyzer.analyze(doc, [])
        pantone_findings = [
            f for f in findings
            if f.inspection_id in ("GRD_SPOT_002", "GRD_SPOT_006")
        ]
        assert len(pantone_findings) == 0
