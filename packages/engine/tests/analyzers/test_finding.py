"""Tests for Finding dataclass and Severity enum."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Finding, Severity


class TestSeverity:
    """Test Severity enum."""

    def test_values(self) -> None:
        assert Severity.AGROUND == "aground"
        assert Severity.SQUALL == "squall"
        assert Severity.ADVISORY == "advisory"

    def test_string_comparison(self) -> None:
        assert Severity.AGROUND == "aground"
        assert str(Severity.AGROUND) == "aground"


class TestFinding:
    """Test Finding dataclass."""

    def test_create_minimal(self) -> None:
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

    def test_create_full(self) -> None:
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

    def test_frozen(self) -> None:
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
