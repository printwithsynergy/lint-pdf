"""Tests for the customer-submitted custom report domain validator."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from siftpdf.api.routes.branding import validate_custom_domain


class TestValidCustomDomains:
    @staticmethod
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("reports.acmeprint.com", "reports.acmeprint.com"),
            ("Reports.ACME.com", "reports.acme.com"),
            ("  reports.acme.com  ", "reports.acme.com"),
            ("reports.acme.com.", "reports.acme.com"),  # trailing dot stripped
            ("a.b.c.d.e.example.co.uk", "a.b.c.d.e.example.co.uk"),
            ("pdf-reports.client-studio.io", "pdf-reports.client-studio.io"),
        ],
    )
    def test_accepts_and_normalizes(raw: str, expected: str) -> None:
        assert validate_custom_domain(raw) == expected


class TestRejectedFormats:
    @staticmethod
    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "not a domain",
            "no-dot",
            "http://reports.acme.com",
            "https://reports.acme.com",
            "reports.acme.com/path",
            "reports.acme.com:443",
            "-reports.acme.com",  # leading hyphen
            "reports..acme.com",  # double dot
            "a" * 254 + ".com",  # total length > 253
        ],
    )
    def test_rejects_invalid_format(bad: str) -> None:
        with pytest.raises(HTTPException) as exc:
            validate_custom_domain(bad)
        assert exc.value.status_code == 422


class TestBlocklist:
    @staticmethod
    @pytest.mark.parametrize(
        "blocked",
        [
            "lintpdf.com",
            "api.lintpdf.com",
            "app.lintpdf.com",
            "reports.lintpdf.com",
            "anything.lintpdf.com",
            "malicious.railway.app",
            "svc.railway.internal",
            "example.com",
            "foo.example.com",
            "test.test",
            "foo.invalid",
            "foo.local",
        ],
    )
    def test_rejects_reserved_hosts(blocked: str) -> None:
        with pytest.raises(HTTPException) as exc:
            validate_custom_domain(blocked)
        assert exc.value.status_code == 422
        assert "reserved" in exc.value.detail.lower()
