"""Tests for the SDK's ``LintPDF.reports()`` method.

These exercise the wire contract — URL, headers, body payload — using
``pytest-httpx`` to stub the engine. The engine's own behavior (inline
vs url, idempotency token math) is covered in the engine test suite;
here we only verify the client shapes the request correctly and maps
the response into ``ReportArtifact`` / ``ReportsResult`` objects.
"""

from __future__ import annotations

import pytest

from lintpdf import LintPDF, ReportArtifact, ReportsResult


@pytest.fixture
def client() -> LintPDF:
    return LintPDF(api_key="lpdf_test", base_url="https://api.example.com")


def _reports_url() -> str:
    return "https://api.example.com/api/v1/jobs/abc-123/reports"


def test_reports_returns_envelope_and_artifacts(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url=_reports_url(),
        method="POST",
        json={
            "reports": [
                {
                    "format": "json",
                    "url": None,
                    "token": None,
                    "expires_at": None,
                    "data": {"findings": [{"severity": "error"}]},
                    "content_type": "application/json",
                },
                {
                    "format": "annotated_pdf",
                    "url": "https://reports.example.com/r/tok_pdf.pdf",
                    "token": "tok_pdf",
                    "expires_at": "2026-05-01T00:00:00Z",
                    "data": None,
                    "content_type": None,
                },
            ]
        },
    )

    result = client.reports(
        "abc-123",
        formats=[
            {"format": "json", "return": "inline"},
            {"format": "annotated_pdf", "return": "url"},
        ],
    )

    assert isinstance(result, ReportsResult)
    assert len(result) == 2

    json_row = result.by_format("json")
    assert isinstance(json_row, ReportArtifact)
    assert json_row.url is None
    assert json_row.data == {"findings": [{"severity": "error"}]}
    assert json_row.content_type == "application/json"

    pdf_row = result.by_format("annotated_pdf")
    assert pdf_row is not None
    assert pdf_row.url == "https://reports.example.com/r/tok_pdf.pdf"
    assert pdf_row.token == "tok_pdf"
    assert pdf_row.data is None


def test_reports_sends_idempotency_key_header(
    httpx_mock, client: LintPDF
) -> None:
    httpx_mock.add_response(
        url=_reports_url(),
        method="POST",
        json={"reports": []},
    )

    client.reports(
        "abc-123",
        formats=["html"],
        idempotency_key="invoice-42",
    )

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers.get("Idempotency-Key") == "invoice-42"
    assert request.headers.get("Authorization") == "Bearer lpdf_test"


def test_reports_omits_idempotency_key_when_none(
    httpx_mock, client: LintPDF
) -> None:
    httpx_mock.add_response(
        url=_reports_url(),
        method="POST",
        json={"reports": []},
    )

    client.reports("abc-123", formats=["html"])

    request = httpx_mock.get_request()
    assert request is not None
    assert "Idempotency-Key" not in request.headers


def test_reports_forwards_optional_knobs(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url=_reports_url(),
        method="POST",
        json={"reports": []},
    )

    client.reports(
        "abc-123",
        formats=["html", "pdf"],
        branding={"name": "Acme", "primary_color": "#ff0055"},
        expiry_days=14,
        detail_level="comprehensive",
        summary_page="prepend",
    )

    request = httpx_mock.get_request()
    body = request.read()
    assert b'"formats":["html","pdf"]' in body.replace(b" ", b"")
    assert b'"expiry_days":14' in body.replace(b" ", b"")
    assert b'"detail_level":"comprehensive"' in body.replace(b" ", b"")
    assert b'"summary_page":"prepend"' in body.replace(b" ", b"")
    assert b'"branding"' in body
