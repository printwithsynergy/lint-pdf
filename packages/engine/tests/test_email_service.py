"""Tests for the Resend-backed email service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lintpdf.email.service import (
    EmailResult,
    configure_email,
    get_email_client,
    send_api_key_issued,
    send_job_complete,
    send_overage_started,
    send_rate_limit_warning,
    send_report,
    set_email_client,
)

TEST_RESEND_API_KEY = "re_test_key_123"
TEST_API_KEY = "gnd_live_abc123"


@pytest.fixture(autouse=True)
def _reset_email_client():
    """Ensure email client is reset before and after each test."""
    set_email_client(None)
    yield
    set_email_client(None)


@pytest.fixture
def mock_email_client() -> MagicMock:
    """Install and return a mock email client."""
    client = MagicMock()
    client.send.return_value = {"id": "email_abc123"}
    set_email_client(client)
    return client


class TestConfigureEmail:
    """Tests for configure_email initialization."""

    @staticmethod
    def test_configure_sets_client() -> None:
        """configure_email should initialize the Resend client."""
        import lintpdf.email.service as svc

        svc._resend_client = None
        mock_resend = MagicMock()
        mock_resend.Emails = MagicMock()
        with patch.dict("sys.modules", {"resend": mock_resend}):
            configure_email(TEST_RESEND_API_KEY)
            assert mock_resend.api_key == TEST_RESEND_API_KEY
            assert get_email_client() is mock_resend.Emails

    @staticmethod
    def test_configure_only_runs_once(mock_email_client: MagicMock) -> None:
        """configure_email should be idempotent once initialized."""
        original = get_email_client()
        configure_email("re_different_key")
        assert get_email_client() is original

    @staticmethod
    def test_configure_custom_from_address() -> None:
        """configure_email should accept a custom from address."""
        import lintpdf.email.service as svc

        svc._email_state["client"] = None
        with patch("lintpdf.email.service.resend", create=True) as mock_resend:
            mock_resend.Emails = MagicMock()
            configure_email("re_key", from_address="Custom <custom@example.com>")
            assert svc._email_state["from_address"] == "Custom <custom@example.com>"
            # Reset
            svc._email_state["from_address"] = "LintPDF <noreply@thinkneverland.com>"


class TestSetEmailClient:
    """Tests for set_email_client (test injection)."""

    @staticmethod
    def test_set_and_get() -> None:
        client = MagicMock()
        set_email_client(client)
        assert get_email_client() is client

    @staticmethod
    def test_set_none_clears() -> None:
        set_email_client(MagicMock())
        set_email_client(None)
        assert get_email_client() is None


class TestSendApiKeyIssued:
    """Tests for send_api_key_issued."""

    @staticmethod
    def test_success(mock_email_client: MagicMock) -> None:
        result = send_api_key_issued(
            to="user@example.com",
            tenant_name="Acme Corp",
            api_key=TEST_API_KEY,
        )
        assert result.success is True
        assert result.email_id == "email_abc123"
        assert result.error is None

        mock_email_client.send.assert_called_once()
        call_args = mock_email_client.send.call_args[0][0]
        assert call_args["to"] == ["user@example.com"]
        assert "Acme Corp" in call_args["subject"]
        assert TEST_API_KEY in call_args["html"]

    @staticmethod
    def test_no_client_configured() -> None:
        result = send_api_key_issued(
            to="user@example.com",
            tenant_name="Acme Corp",
            api_key=TEST_API_KEY,
        )
        assert result.success is False
        assert result.error == "Email client not configured"

    @staticmethod
    def test_invalid_email_rejected(mock_email_client: MagicMock) -> None:
        result = send_api_key_issued(
            to="not-an-email",
            tenant_name="Acme Corp",
            api_key=TEST_API_KEY,
        )
        assert result.success is False
        assert result.error == "Invalid email address"
        mock_email_client.send.assert_not_called()

    @staticmethod
    def test_send_failure(mock_email_client: MagicMock) -> None:
        mock_email_client.send.side_effect = Exception("API error")
        result = send_api_key_issued(
            to="user@example.com",
            tenant_name="Acme Corp",
            api_key=TEST_API_KEY,
        )
        assert result.success is False
        assert result.error == "Send failed"


class TestSendJobComplete:
    """Tests for send_job_complete."""

    @staticmethod
    def test_no_findings(mock_email_client: MagicMock) -> None:
        result = send_job_complete(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-001",
            file_name="brochure.pdf",
            finding_count=0,
        )
        assert result.success is True
        call_args = mock_email_client.send.call_args[0][0]
        assert "passed" in call_args["subject"]

    @staticmethod
    def test_with_findings(mock_email_client: MagicMock) -> None:
        result = send_job_complete(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-001",
            file_name="brochure.pdf",
            finding_count=5,
        )
        assert result.success is True
        call_args = mock_email_client.send.call_args[0][0]
        assert "5 issue(s)" in call_args["subject"]
        assert "brochure.pdf" in call_args["subject"]

    @staticmethod
    def test_html_contains_job_details(mock_email_client: MagicMock) -> None:
        send_job_complete(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-xyz-789",
            file_name="report.pdf",
            finding_count=3,
        )
        call_args = mock_email_client.send.call_args[0][0]
        assert "job-xyz-789" in call_args["html"]
        assert "Acme Corp" in call_args["html"]
        assert "report.pdf" in call_args["html"]


class TestSendRateLimitWarning:
    """Tests for send_rate_limit_warning."""

    @staticmethod
    def test_percentage_calculation(mock_email_client: MagicMock) -> None:
        result = send_rate_limit_warning(
            to="admin@example.com",
            tenant_name="Acme Corp",
            used=80,
            limit=100,
        )
        assert result.success is True
        call_args = mock_email_client.send.call_args[0][0]
        assert "80%" in call_args["subject"]

    @staticmethod
    def test_zero_limit_shows_100_percent(mock_email_client: MagicMock) -> None:
        send_rate_limit_warning(
            to="admin@example.com",
            tenant_name="Acme Corp",
            used=5,
            limit=0,
        )
        call_args = mock_email_client.send.call_args[0][0]
        assert "100%" in call_args["subject"]

    @staticmethod
    def test_html_contains_usage_info(mock_email_client: MagicMock) -> None:
        send_rate_limit_warning(
            to="admin@example.com",
            tenant_name="Acme Corp",
            used=90,
            limit=100,
        )
        call_args = mock_email_client.send.call_args[0][0]
        html = call_args["html"]
        assert "90" in html
        assert "100" in html


class TestSendOverageStarted:
    """Tests for send_overage_started."""

    @staticmethod
    def test_dollar_formatting(mock_email_client: MagicMock) -> None:
        result = send_overage_started(
            to="billing@example.com",
            tenant_name="Acme Corp",
            used=120,
            limit=100,
            rate_cents=10,
            cost_cents=200,
        )
        assert result.success is True
        call_args = mock_email_client.send.call_args[0][0]
        html = call_args["html"]
        assert "$0.10" in html  # rate
        assert "$2.00" in html  # cost


class TestSendReport:
    """Tests for send_report."""

    @staticmethod
    def test_passed_report(mock_email_client: MagicMock) -> None:
        result = send_report(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-001",
            report_url="https://api.lintpdf.com/r/abc123",
            finding_count=0,
            passed=True,
        )
        assert result.success is True
        call_args = mock_email_client.send.call_args[0][0]
        assert "passed" in call_args["subject"]
        assert "PASS" in call_args["html"]
        assert "https://api.lintpdf.com/r/abc123" in call_args["html"]

    @staticmethod
    def test_failed_report(mock_email_client: MagicMock) -> None:
        send_report(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-001",
            report_url="https://api.lintpdf.com/r/abc123",
            finding_count=3,
            passed=False,
        )
        call_args = mock_email_client.send.call_args[0][0]
        assert "3 issue(s)" in call_args["subject"]
        assert "FAIL" in call_args["html"]

    @staticmethod
    def test_custom_branding(mock_email_client: MagicMock) -> None:
        send_report(
            to="user@example.com",
            tenant_name="Acme Corp",
            job_id="job-001",
            report_url="https://api.lintpdf.com/r/abc",
            finding_count=0,
            passed=True,
            brand_name="AcmePrint",
            brand_primary_color="#ff0000",
        )
        call_args = mock_email_client.send.call_args[0][0]
        html = call_args["html"]
        assert "AcmePrint" in html
        assert "#ff0000" in html


class TestEmailValidation:
    """Tests for email address validation in _send."""

    @pytest.mark.parametrize(
        "invalid_email",
        [
            "not-an-email",
            "missing@tld",
            "@no-local.com",
            "spaces in@email.com",
            "newline\n@evil.com",
            "carriage\r@evil.com",
            "",
        ],
    )
    def test_invalid_emails_rejected(
        self, mock_email_client: MagicMock, invalid_email: str
    ) -> None:
        result = send_api_key_issued(
            to=invalid_email,
            tenant_name="Test",
            api_key="key",
        )
        assert result.success is False
        assert result.error == "Invalid email address"
        mock_email_client.send.assert_not_called()

    @pytest.mark.parametrize(
        "valid_email",
        [
            "user@example.com",
            "first.last@domain.org",
            "user+tag@domain.co.uk",
            "name123@test.io",
        ],
    )
    @staticmethod
    def test_valid_emails_accepted(mock_email_client: MagicMock, valid_email: str) -> None:
        result = send_api_key_issued(
            to=valid_email,
            tenant_name="Test",
            api_key="key",
        )
        assert result.success is True
        mock_email_client.send.assert_called_once()
        mock_email_client.send.reset_mock()


class TestEmailResult:
    """Tests for the EmailResult dataclass."""

    @staticmethod
    def test_success_result() -> None:
        r = EmailResult(success=True, email_id="abc123")
        assert r.success is True
        assert r.email_id == "abc123"
        assert r.error is None

    @staticmethod
    def test_failure_result() -> None:
        r = EmailResult(success=False, error="Something failed")
        assert r.success is False
        assert r.email_id is None
        assert r.error == "Something failed"

    @staticmethod
    def test_send_returns_none_email_id_on_non_dict(mock_email_client: MagicMock) -> None:
        """If the Resend API returns a non-dict, email_id should be None."""
        mock_email_client.send.return_value = "not-a-dict"
        result = send_api_key_issued(
            to="user@example.com",
            tenant_name="Test",
            api_key="key",
        )
        assert result.success is True
        assert result.email_id is None
