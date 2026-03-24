"""Tests for Finding dataclass with source/category AI extensions."""

from __future__ import annotations

from lintpdf.analyzers.finding import Finding, Severity


class TestFindingSourceAndCategory:
    """Test that Finding supports source and category fields."""

    @staticmethod
    def test_default_source_is_engine() -> None:
        f = Finding(
            inspection_id="LPDF_FONT_001",
            severity=Severity.ERROR,
            message="Font not embedded",
        )
        assert f.source == "engine"

    @staticmethod
    def test_default_category_is_empty() -> None:
        f = Finding(
            inspection_id="LPDF_FONT_001",
            severity=Severity.ERROR,
            message="Font not embedded",
        )
        assert f.category == ""

    @staticmethod
    def test_ai_source() -> None:
        f = Finding(
            inspection_id="AI_SPELL_001",
            severity=Severity.ADVISORY,
            message="Misspelling detected",
            source="ai",
            category="content_quality",
        )
        assert f.source == "ai"
        assert f.category == "content_quality"

    @staticmethod
    def test_finding_is_frozen() -> None:
        f = Finding(
            inspection_id="AI_BC_001",
            severity=Severity.ADVISORY,
            message="Barcode decoded",
            source="ai",
            category="barcode",
        )
        with __import__("pytest").raises(AttributeError):
            f.source = "engine"  # type: ignore[misc]

    @staticmethod
    def test_backward_compat_no_source_kwarg() -> None:
        """Existing engine code that doesn't pass source/category should still work."""
        f = Finding(
            inspection_id="LPDF_IMG_001",
            severity=Severity.WARNING,
            message="Low resolution image",
            page_num=1,
            details={"dpi": 72},
            iso_clause="ISO 32000-2:2020 8.9",
        )
        assert f.source == "engine"
        assert f.category == ""
        assert f.page_num == 1
        assert f.details == {"dpi": 72}

    @staticmethod
    def test_all_severity_values() -> None:
        """Severity enum has exactly three members."""
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"
        assert Severity.ADVISORY == "advisory"
        assert len(Severity) == 3

    @staticmethod
    def test_finding_equality() -> None:
        """Two findings with identical fields should be equal (frozen dataclass)."""
        f1 = Finding(
            inspection_id="AI_BC_001",
            severity=Severity.ADVISORY,
            message="Decoded barcode",
            source="ai",
            category="barcode",
        )
        f2 = Finding(
            inspection_id="AI_BC_001",
            severity=Severity.ADVISORY,
            message="Decoded barcode",
            source="ai",
            category="barcode",
        )
        assert f1 == f2

    @staticmethod
    def test_finding_inequality_on_source() -> None:
        f_engine = Finding(
            inspection_id="LPDF_BC_001",
            severity=Severity.ADVISORY,
            message="Barcode check",
            source="engine",
        )
        f_ai = Finding(
            inspection_id="LPDF_BC_001",
            severity=Severity.ADVISORY,
            message="Barcode check",
            source="ai",
        )
        assert f_engine != f_ai

    @staticmethod
    def test_finding_with_bbox() -> None:
        f = Finding(
            inspection_id="AI_BC_001",
            severity=Severity.ADVISORY,
            message="Barcode at location",
            source="ai",
            category="barcode",
            bbox=(100.0, 200.0, 300.0, 400.0),
        )
        assert f.bbox == (100.0, 200.0, 300.0, 400.0)

    @staticmethod
    def test_finding_with_object_metadata() -> None:
        f = Finding(
            inspection_id="AI_LOGO_001",
            severity=Severity.WARNING,
            message="Logo not verified",
            source="ai",
            category="logo_verification",
            object_id="logo_1",
            object_type="logo",
        )
        assert f.object_id == "logo_1"
        assert f.object_type == "logo"
