"""Tests for the Resend email service."""

from __future__ import annotations

# skipcq: PYL-R0201
from unittest.mock import MagicMock

import pytest

from grounded.email.service import (
    EmailResult,
    get_email_client,
    send_api_key_issued,
    send_job_complete,
    send_rate_limit_warning,
    set_email_client,
)


class FakeEmails:
    """Fake Resend Emails client that records calls."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send(self, params: dict) -> dict:
        self.calls.append(params)
        return {"id": f"fake-email-{len(self.calls)}"}


@pytest.fixture
def fake_emails() -> FakeEmails:
    client = FakeEmails()
    set_email_client(client)
    yield client
    set_email_client(None)


class TestSendApiKeyIssued:
    def test_sends_email(self, fake_emails: FakeEmails) -> None:
        result = send_api_key_issued(
            to="dev@example.com",
            tenant_name="Acme Corp",
            api_key="gnd_abc123",
        )
        assert result.success is True
        assert result.email_id == "fake-email-1"
        assert len(fake_emails.calls) == 1
        call = fake_emails.calls[0]
        assert call["to"] == ["dev@example.com"]
        assert "Acme Corp" in call["subject"]
        assert "gnd_abc123" in call["html"]

    def test_contains_save_warning(self, fake_emails: FakeEmails) -> None:
        send_api_key_issued(
            to="dev@example.com",
            tenant_name="Test",
            api_key="gnd_xyz",
        )
        html = fake_emails.calls[0]["html"]
        assert "Save this key now" in html


class TestSendJobComplete:
    def test_sends_with_findings(self, fake_emails: FakeEmails) -> None:
        result = send_job_complete(
            to="dev@example.com",
            tenant_name="Acme Corp",
            job_id="job-123",
            file_name="brochure.pdf",
            finding_count=5,
        )
        assert result.success is True
        call = fake_emails.calls[0]
        assert "5 issue(s)" in call["subject"]
        assert "brochure.pdf" in call["html"]

    def test_sends_with_zero_findings(self, fake_emails: FakeEmails) -> None:
        send_job_complete(
            to="dev@example.com",
            tenant_name="Acme Corp",
            job_id="job-456",
            file_name="clean.pdf",
            finding_count=0,
        )
        call = fake_emails.calls[0]
        assert "passed" in call["subject"]


class TestSendRateLimitWarning:
    def test_sends_warning(self, fake_emails: FakeEmails) -> None:
        result = send_rate_limit_warning(
            to="dev@example.com",
            tenant_name="Acme Corp",
            used=90,
            limit=100,
        )
        assert result.success is True
        call = fake_emails.calls[0]
        assert "90%" in call["subject"]
        assert "90" in call["html"]
        assert "100" in call["html"]

    def test_100_percent(self, fake_emails: FakeEmails) -> None:
        send_rate_limit_warning(
            to="dev@example.com",
            tenant_name="Test",
            used=100,
            limit=100,
        )
        assert "100%" in fake_emails.calls[0]["subject"]


class TestEmailClientNotConfigured:
    def test_returns_failure(self) -> None:
        set_email_client(None)
        result = send_api_key_issued(
            to="dev@example.com",
            tenant_name="Test",
            api_key="gnd_xyz",
        )
        assert result.success is False
        assert result.error == "Email client not configured"


class TestEmailSendFailure:
    def test_returns_failure_on_exception(self) -> None:
        broken = MagicMock()
        broken.send.side_effect = RuntimeError("Network error")
        set_email_client(broken)

        result = send_api_key_issued(
            to="dev@example.com",
            tenant_name="Test",
            api_key="gnd_xyz",
        )
        assert result.success is False
        assert result.error == "Send failed"
        set_email_client(None)


class TestGetEmailClient:
    def test_returns_none_by_default(self) -> None:
        set_email_client(None)
        assert get_email_client() is None

    def test_returns_set_client(self) -> None:
        mock = MagicMock()
        set_email_client(mock)
        assert get_email_client() is mock
        set_email_client(None)


class TestEmailResult:
    def test_defaults(self) -> None:
        result = EmailResult(success=True)
        assert result.email_id is None
        assert result.error is None

    def test_with_id(self) -> None:
        result = EmailResult(success=True, email_id="msg-123")
        assert result.email_id == "msg-123"
