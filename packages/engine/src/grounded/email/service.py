"""Resend-backed email service for tenant notifications."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Module-level client — set via configure_email() or set_email_client()
_resend_client: Any = None
_from_address: str = "Grounded <noreply@thinkneverland.com>"
_email_lock = threading.Lock()


def configure_email(api_key: str, *, from_address: str | None = None) -> None:
    """Initialize the Resend client.

    Args:
        api_key: Resend API key.
        from_address: Sender address override.
    """
    global _resend_client, _from_address  # skipcq: PYL-W0603
    with _email_lock:
        if _resend_client is not None:
            return
        import resend

        resend.api_key = api_key
        _resend_client = resend.Emails
        if from_address:
            _from_address = from_address


def set_email_client(client: Any) -> None:
    """Override the email client (for testing)."""
    global _resend_client  # skipcq: PYL-W0603
    _resend_client = client


def get_email_client() -> Any:
    """Return the current email client."""
    return _resend_client


@dataclass
class EmailResult:
    """Result of sending an email."""

    success: bool
    email_id: str | None = None
    error: str | None = None


def send_api_key_issued(*, to: str, tenant_name: str, api_key: str) -> EmailResult:
    """Send API key notification to a new tenant.

    Args:
        to: Recipient email address.
        tenant_name: Name of the tenant organization.
        api_key: The raw API key (shown only once).
    """
    subject = f"Your Grounded API Key — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e293b;">Welcome to Grounded</h2>
  <p>Your API key for <strong>{tenant_name}</strong> has been issued.</p>
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <code style="font-size: 14px; word-break: break-all;">{api_key}</code>
  </div>
  <p style="color: #ef4444; font-size: 14px;">
    <strong>Save this key now.</strong> It cannot be retrieved after this email.
  </p>
  <p style="font-size: 14px; color: #64748b;">
    Include it in your requests as:<br>
    <code>Authorization: Bearer YOUR_API_KEY</code>
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_job_complete(
    *, to: str, tenant_name: str, job_id: str, file_name: str, finding_count: int
) -> EmailResult:
    """Notify tenant that a preflight job completed.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        job_id: The completed job ID.
        file_name: Original uploaded file name.
        finding_count: Number of findings detected.
    """
    status_text = "passed" if finding_count == 0 else f"found {finding_count} issue(s)"
    subject = f"Preflight {status_text} — {file_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e293b;">Preflight Complete</h2>
  <p>Job for <strong>{file_name}</strong> has finished.</p>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr>
      <td style="padding: 8px; color: #64748b;">Organization</td>
      <td style="padding: 8px;"><strong>{tenant_name}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Job ID</td>
      <td style="padding: 8px;"><code>{job_id}</code></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Findings</td>
      <td style="padding: 8px;"><strong>{finding_count}</strong></td>
    </tr>
  </table>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_rate_limit_warning(*, to: str, tenant_name: str, used: int, limit: int) -> EmailResult:
    """Warn tenant they are approaching or have hit their daily rate limit.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        used: Current daily usage count.
        limit: Daily rate limit.
    """
    pct = int((used / limit) * 100) if limit > 0 else 100
    subject = f"Rate limit {pct}% — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #f59e0b;">Rate Limit Warning</h2>
  <p><strong>{tenant_name}</strong> has used <strong>{used}</strong> of <strong>{limit}</strong> daily requests ({pct}%).</p>
  <p style="font-size: 14px; color: #64748b;">
    Upgrade your plan to increase your daily limit.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_overage_started(
    *, to: str, tenant_name: str, used: int, limit: int, rate_cents: int, cost_cents: int
) -> EmailResult:
    """Notify tenant that billable overage charges have begun.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        used: Current daily usage count.
        limit: Daily rate limit (included jobs).
        rate_cents: Per-job overage rate in cents.
        cost_cents: Current total overage cost in cents.
    """
    rate_dollars = f"${rate_cents / 100:.2f}"
    cost_dollars = f"${cost_cents / 100:.2f}"
    subject = f"Overage billing active — {tenant_name}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #f59e0b;">Overage Billing Active</h2>
  <p><strong>{tenant_name}</strong> has used <strong>{used}</strong> of <strong>{limit}</strong> daily included jobs.</p>
  <p>Additional jobs are being charged at <strong>{rate_dollars}/job</strong>.</p>
  <p>Current overage cost today: <strong>{cost_dollars}</strong></p>
  <p style="font-size: 14px; color: #64748b;">
    Upgrade your plan for more included jobs, or set a spending cap in your dashboard.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


def send_report(
    *,
    to: str,
    tenant_name: str,
    job_id: str,
    report_url: str,
    finding_count: int,
    passed: bool,
    brand_name: str = "Grounded",
    brand_primary_color: str = "#1a3a7a",
) -> EmailResult:
    """Send a preflight report email with link to hosted report.

    Args:
        to: Recipient email address.
        tenant_name: Tenant organization name.
        job_id: The completed job ID.
        report_url: URL to the hosted interactive report.
        finding_count: Number of findings detected.
        passed: Whether the document passed preflight.
        brand_name: White-label brand name.
        brand_primary_color: Brand primary color.
    """
    status_text = "passed" if passed else f"found {finding_count} issue(s)"
    subject = f"Preflight Report — {status_text}"
    html = f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: {brand_primary_color};">{brand_name} Preflight Report</h2>
  <p>Preflight for <strong>{tenant_name}</strong> job <code>{job_id}</code> has {status_text}.</p>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr>
      <td style="padding: 8px; color: #64748b;">Status</td>
      <td style="padding: 8px;"><strong>{"PASS" if passed else "FAIL"}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #64748b;">Findings</td>
      <td style="padding: 8px;"><strong>{finding_count}</strong></td>
    </tr>
  </table>
  <div style="margin: 24px 0;">
    <a href="{report_url}" style="display: inline-block; padding: 12px 24px; background: {brand_primary_color}; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
      View Interactive Report
    </a>
  </div>
  <p style="font-size: 12px; color: #9ca3af;">
    This report is hosted and may expire. Save or print it for permanent records.
  </p>
</div>"""
    return _send(to=to, subject=subject, html=html)


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _send(*, to: str, subject: str, html: str) -> EmailResult:
    """Send an email via the configured client.

    Returns:
        EmailResult with success status.
    """
    # Validate email to prevent header injection
    if not _EMAIL_RE.match(to) or "\n" in to or "\r" in to:
        logger.warning("Invalid email address rejected: %s", to)
        return EmailResult(success=False, error="Invalid email address")

    if _resend_client is None:
        logger.warning("Email client not configured — skipping send to %s", to)
        return EmailResult(success=False, error="Email client not configured")

    try:
        result = _resend_client.send(
            {
                "from": _from_address,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else None
        return EmailResult(success=True, email_id=email_id)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return EmailResult(success=False, error="Send failed")
