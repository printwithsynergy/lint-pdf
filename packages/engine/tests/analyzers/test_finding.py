"""Tests for Finding dataclass and Severity enum."""

from __future__ import annotations

from lintpdf.analyzers.finding import Finding, Severity


class TestSeverity:
    """Test Severity enum."""

    @staticmethod
    def test_values() -> None:
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"
        assert Severity.ADVISORY == "advisory"

    @staticmethod
    def test_string_comparison() -> None:
        assert Severity.ERROR == "error"
        assert str(Severity.ERROR) == "error"


class TestFinding:
    """Test Finding dataclass."""

    @staticmethod
    def test_create_minimal() -> None:
        f = Finding(
            inspection_id="GRD_TEST_001",
            severity=Severity.WARNING,
            message="Test finding",
        )
        assert f.inspection_id == "GRD_TEST_001"
        assert f.severity == Severity.WARNING
        assert f.message == "Test finding"
        assert f.page_num == 0
        assert f.details == {}
        assert f.iso_clause == ""

    @staticmethod
    def test_create_full() -> None:
        f = Finding(
            inspection_id="GRD_IMG_001",
            severity=Severity.ERROR,
            message="Low resolution image",
            page_num=3,
            details={"dpi": 72},
            iso_clause="ISO 32000-2:2020 8.9",
        )
        assert f.page_num == 3
        assert f.details["dpi"] == 72
        assert f.iso_clause == "ISO 32000-2:2020 8.9"

    @staticmethod
    def test_frozen() -> None:
        f = Finding(
            inspection_id="GRD_TEST_001",
            severity=Severity.WARNING,
            message="Test",
        )
        try:
            f.message = "Changed"  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except AttributeError:
            pass
