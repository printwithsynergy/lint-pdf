"""Tests for veraPDF-backed conformance findings.

Covers Batch 3:
  - T1-CMP01 → LPDF_PDFX_CONF
  - T4-A01  → LPDF_UA_CONF
  - T4-A02  → LPDF_PDFA_CONF
"""

from __future__ import annotations

from unittest.mock import patch

from lintpdf.analyzers.finding import Severity
from lintpdf.conformance.verapdf_runner import (
    _CONF_TO_VERAPDF_PDFA,
    _CONF_TO_VERAPDF_PDFX,
    _summarise_failures,
    run_verapdf_checks,
)

_FAKE_PDF = b"%PDF-1.6\n"


class TestConformanceMaps:
    @staticmethod
    def test_pdfx_family_complete() -> None:
        """Every PDF/X flavour the engine recognises has a veraPDF profile."""
        for key in (
            "pdfx1a",
            "pdfx1a2003",
            "pdfx3",
            "pdfx32003",
            "pdfx4",
            "pdfx4p",
            "pdfx5",
            "pdfx6",
        ):
            assert key in _CONF_TO_VERAPDF_PDFX, f"missing: {key}"

    @staticmethod
    def test_pdfa_family_complete() -> None:
        for key in ("pdfa1b", "pdfa2b", "pdfa2u", "pdfa3b", "pdfa3u", "pdfa4"):
            assert key in _CONF_TO_VERAPDF_PDFA, f"missing: {key}"


class TestSummariseFailures:
    @staticmethod
    def test_dedupes_by_clause_and_test() -> None:
        raw = [
            {
                "message": "first",
                "details": {"clause": "6.1", "test_number": "1", "failed_checks": 3},
            },
            {
                "message": "dup",
                "details": {"clause": "6.1", "test_number": "1", "failed_checks": 3},
            },
            {
                "message": "second",
                "details": {"clause": "6.2", "test_number": "2", "failed_checks": 1},
            },
        ]
        out = _summarise_failures(raw)
        assert len(out) == 2
        assert out[0]["clause"] == "6.1"
        assert out[1]["clause"] == "6.2"

    @staticmethod
    def test_caps_at_25() -> None:
        raw = [
            {
                "message": f"r{i}",
                "details": {"clause": str(i), "test_number": "1", "failed_checks": 1},
            }
            for i in range(100)
        ]
        assert len(_summarise_failures(raw)) == 25


class TestUnconfigured:
    @staticmethod
    def test_no_verapdf_url_silent() -> None:
        """When veraPDF URL isn't configured, no findings emit."""
        with patch(
            "lintpdf.conformance.verapdf_runner.is_verapdf_configured",
            return_value=False,
        ):
            assert run_verapdf_checks(_FAKE_PDF, conformance="pdfx4", enabled_ua=True) == []

    @staticmethod
    def test_metadata_out_when_not_configured() -> None:
        """``metadata_out`` records why veraPDF did not run."""
        meta: dict = {}
        with patch(
            "lintpdf.conformance.verapdf_runner.is_verapdf_configured",
            return_value=False,
        ):
            assert (
                run_verapdf_checks(
                    _FAKE_PDF,
                    conformance="pdfx4",
                    enabled_ua=True,
                    metadata_out=meta,
                )
                == []
            )
        assert meta.get("configured") is False
        assert meta.get("skipped_reason") == "not_configured"

    @staticmethod
    def test_empty_pdf_bytes_silent() -> None:
        assert run_verapdf_checks(b"", conformance="pdfx4", enabled_ua=True) == []


class TestPdfXFinding:
    @staticmethod
    def test_non_conformant_pdfx_fires() -> None:
        mock_failures = [
            {
                "message": "6.1-1 broken",
                "details": {"clause": "6.1", "test_number": "1", "failed_checks": 3},
            }
        ]
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=mock_failures,
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfx4", enabled_ua=False)
            assert len(findings) == 1
            f = findings[0]
            assert f.inspection_id == "LPDF_PDFX_CONF"
            assert f.severity == Severity.ERROR
            assert f.details["conformance"] == "pdfx4"
            assert f.details["verapdf_profile"] == "PDFX_4"
            assert f.details["failure_count"] == 1
            assert f.details["failures"][0]["clause"] == "6.1"

    @staticmethod
    def test_compliant_pdfx_silent() -> None:
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=[],
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfx4", enabled_ua=False)
            assert findings == []


class TestPdfAFinding:
    @staticmethod
    def test_non_conformant_pdfa_fires() -> None:
        mock_failures = [
            {
                "message": "6.2-3 bad",
                "details": {"clause": "6.2", "test_number": "3", "failed_checks": 1},
            }
        ]
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=mock_failures,
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfa2b", enabled_ua=False)
            assert len(findings) == 1
            assert findings[0].inspection_id == "LPDF_PDFA_CONF"
            assert findings[0].details["verapdf_profile"] == "PDFA_2_B"


class TestUaFinding:
    @staticmethod
    def test_non_conformant_ua_fires_when_enabled() -> None:
        mock_failures = [
            {
                "message": "UA-01 Tags",
                "details": {"clause": "1", "test_number": "1", "failed_checks": 2},
            }
        ]
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=mock_failures,
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance=None, enabled_ua=True)
            assert len(findings) == 1
            assert findings[0].inspection_id == "LPDF_UA_CONF"
            assert findings[0].severity == Severity.WARNING

    @staticmethod
    def test_ua_silent_when_not_enabled() -> None:
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=[{"message": "x", "details": {}}],
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance=None, enabled_ua=False)
            assert findings == []


class TestCombinedFlavours:
    @staticmethod
    def test_pdfa_and_ua_together() -> None:
        """A PDF/A + UA profile runs BOTH veraPDF flavours and can emit
        two findings on a single call."""
        call_count = {"n": 0}

        def mock_validate(pdf, *, profile):
            call_count["n"] += 1
            return [{"message": f"fail-{profile}", "details": {"clause": "1", "test_number": "1"}}]

        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                side_effect=mock_validate,
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfa2b", enabled_ua=True)
            ids = {f.inspection_id for f in findings}
            assert ids == {"LPDF_PDFA_CONF", "LPDF_UA_CONF"}
            assert call_count["n"] == 2

    @staticmethod
    def test_pdfx_only_emits_one() -> None:
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                return_value=[{"message": "x", "details": {"clause": "1", "test_number": "1"}}],
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfx4", enabled_ua=False)
            assert [f.inspection_id for f in findings] == ["LPDF_PDFX_CONF"]


class TestVeraException:
    @staticmethod
    def test_verapdf_exception_silent() -> None:
        """If validate_with_verapdf raises (network flake, parse error),
        we return empty and don't block the preflight."""
        with (
            patch("lintpdf.conformance.verapdf_runner.is_verapdf_configured", return_value=True),
            patch(
                "lintpdf.conformance.verapdf_runner.validate_with_verapdf",
                side_effect=RuntimeError("boom"),
            ),
        ):
            findings = run_verapdf_checks(_FAKE_PDF, conformance="pdfx4", enabled_ua=True)
            assert findings == []
