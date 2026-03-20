"""Tests for Finding dataclass and Severity enum."""

from __future__ import annotations

from grounded.analyzers.finding import Finding, Severity


class TestSeverity:
    """Test Severity enum."""

    @staticmethod
    def test_values() -> None:
        assert Severity.AGROUND == "aground"
        assert Severity.SQUALL == "squall"
        assert Severity.ADVISORY == "advisory"

    @staticmethod
    def test_string_comparison() -> None:
        assert Severity.AGROUND == "aground"
        assert str(Severity.AGROUND) == "aground"


class TestFinding:
    """Test Finding dataclass."""

    @staticmethod
    def test_create_minimal() -> None:
        f = Finding(
            inspection_id="GRD_TEST_001",
            severity=Severity.SQUALL,
            message="Test finding",
        )
        assert f.inspection_id == "GRD_TEST_001"
        assert f.severity == Severity.SQUALL
        assert f.message == "Test finding"
        assert f.page_num == 0
        assert f.details == {}
        assert f.iso_clause == ""

    @staticmethod
    def test_create_full() -> None:
        f = Finding(
            inspection_id="GRD_IMG_001",
            severity=Severity.AGROUND,
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
            severity=Severity.SQUALL,
            message="Test",
        )
        try:
            f.message = "Changed"  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except AttributeError:
            pass
