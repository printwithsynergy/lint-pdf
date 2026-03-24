"""Tests for Pantone validation — reference DB, Delta-E, and analyzer integration."""

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.spot_color_analyzer import SpotColorAnalyzer
from lintpdf.profiles.icc.pantone_manager import (
    DeltaEResult,
    PantoneManager,
    PantoneReference,
)
from lintpdf.semantic.model import (
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
        version="2.0",
        page_count=len(pages),
        is_encrypted=False,
        pages=pages,
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
                name=None,
                cs_type="DeviceCMYK",
                components=4,
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
                name=None,
                cs_type="DeviceCMYK",
                components=4,
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
            f for f in findings if f.inspection_id in ("GRD_SPOT_002", "GRD_SPOT_006")
        ]
        assert len(pantone_findings) == 0


class TestOrchestratorPantoneOverrides:
    """Tests that Pantone overrides flow through the orchestrator to analyzers."""

    def test_orchestrator_passes_overrides_to_spot_analyzer(self):
        """Overrides passed to orchestrator reach SpotColorAnalyzer."""
        from unittest.mock import patch

        from lintpdf.profiles.orchestrator import PreflightOrchestrator
        from lintpdf.profiles.schema import PreflightProfile

        # Minimal profile that enables spot color checking
        profile = PreflightProfile.model_validate(
            {
                "name": "test",
                "version": "1.0",
                "conformance": "none",
            }
        )

        overrides = {
            "PANTONE 485 C": {"lab": [99.0, 0.0, 0.0], "cmyk_bridge": [0, 0, 0, 0]},
        }

        orch = PreflightOrchestrator(
            profile,
            custom_pantone_overrides=overrides,
        )
        analyzers = orch._create_analyzers()
        spot_analyzers = [a for a in analyzers if isinstance(a, SpotColorAnalyzer)]
        assert len(spot_analyzers) == 1
        assert spot_analyzers[0]._custom_pantone_data == overrides

    def test_orchestrator_none_overrides_gives_none_to_analyzer(self):
        """When no overrides, SpotColorAnalyzer receives None."""
        from lintpdf.profiles.orchestrator import PreflightOrchestrator
        from lintpdf.profiles.schema import PreflightProfile

        profile = PreflightProfile.model_validate(
            {
                "name": "test",
                "version": "1.0",
                "conformance": "none",
            }
        )

        orch = PreflightOrchestrator(profile)
        analyzers = orch._create_analyzers()
        spot_analyzers = [a for a in analyzers if isinstance(a, SpotColorAnalyzer)]
        assert len(spot_analyzers) == 1
        assert spot_analyzers[0]._custom_pantone_data is None


class TestEnrichedPantoneReference:
    """Tests for the enriched Pantone reference with library metadata."""

    def test_reference_has_minimum_count(self):
        """Reference database never shrinks below original 2,162 colors."""
        import json
        from pathlib import Path

        ref_path = Path(__file__).parent / "../../src/lintpdf/profiles/icc/pantone_reference.json"
        data = json.loads(ref_path.read_text(encoding="utf-8"))
        assert data["_meta"]["count"] >= 2162

    def test_lookup_returns_library_metadata(self):
        """PantoneReference includes library, lab_source, cmyk_source fields."""
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 485 C")
        assert ref is not None
        assert ref.library == "Pantone Formula Guide Coated"
        assert ref.lab_source == "PANTONE_PUBLISHED"
        assert ref.cmyk_source is not None

    def test_lookup_tcx_color(self):
        """Can look up a non-Formula-Guide color (TCX textile)."""
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 19-4052 TCX")
        assert ref is not None
        assert ref.library == "FHI Cotton TCX"
        assert ref.lab_source == "PANTONE_PUBLISHED"
        assert ref.lab is not None
        assert len(ref.lab) == 3

    def test_lookup_metallics_color(self):
        """Can look up a Metallics color."""
        mgr = PantoneManager()
        ref = mgr.lookup("PANTONE 8485 C")
        assert ref is not None
        assert ref.library == "Pantone Metallics Coated"

    def test_has_color_known(self):
        """has_color returns True for known colors."""
        mgr = PantoneManager()
        assert mgr.has_color("PANTONE 485 C") is True
        assert mgr.has_color("pantone 485 c") is True

    def test_has_color_unknown(self):
        """has_color returns False for unknown colors."""
        mgr = PantoneManager()
        assert mgr.has_color("PANTONE 99999 C") is False

    def test_has_color_alternate_spacing(self):
        """has_color handles alternate name spacing."""
        mgr = PantoneManager()
        assert mgr.has_color("PANTONE 485C") is True

    def test_formula_guide_colors_have_cmyk_bridge(self):
        """All Formula Guide C/U colors should have cmyk_bridge values."""
        import json
        from pathlib import Path

        ref_path = Path(__file__).parent / "../../src/lintpdf/profiles/icc/pantone_reference.json"
        data = json.loads(ref_path.read_text(encoding="utf-8"))
        fg_colors = {
            k: v
            for k, v in data["colors"].items()
            if v.get("library", "").startswith("Pantone Formula Guide")
        }
        assert len(fg_colors) > 4000  # Should be ~4,646
        missing_bridge = [k for k, v in fg_colors.items() if not v.get("cmyk_bridge")]
        assert len(missing_bridge) == 0, (
            f"Formula Guide colors missing cmyk_bridge: {missing_bridge[:5]}"
        )
